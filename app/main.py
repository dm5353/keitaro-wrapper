from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.keitaro import keitaro_client
from app.models import CampaignLog, RemovedStreamOffer, StreamAuditLog
from app.schemas import CampaignCreate

app = FastAPI(title="Keitaro Wrapper")
templates = Jinja2Templates(directory="app/templates")


class StreamOffersUpdate(BaseModel):
    offers: list[dict]


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/api/offers")
async def search_offers(q: str = ""):
    return await keitaro_client.get_offers(q)


@app.get("/api/dictionaries")
async def get_dictionaries():
    return await keitaro_client.get_defaults()


@app.get("/api/logs")
async def get_logs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CampaignLog).order_by(CampaignLog.id.desc()).limit(20))
    return result.scalars().all()


@app.post("/api/campaigns")
async def create_campaign(payload: CampaignCreate, db: AsyncSession = Depends(get_db)):
    campaign = await keitaro_client.create_campaign_with_streams(payload)

    # Сохраняем запись о созданной кампании в локальную БД
    log = CampaignLog(
        keitaro_campaign_id=campaign["id"],
        name=payload.name,
        geo=",".join(payload.parsed_countries()),
        offer_id=payload.offer_id,
    )
    db.add(log)
    await db.commit()

    return {"status": "ok", "campaign": campaign}


# --- Роуты для Редактора существующей кампании ---

@app.get("/api/campaigns/{campaign_id}/streams")
async def get_streams(campaign_id: int, db: AsyncSession = Depends(get_db)):
    streams = await keitaro_client.get_campaign_streams(campaign_id)
    offers_list = await keitaro_client.get_offers("")
    offers_map = {o["id"]: o["name"] for o in offers_list}

    # Достаём из локальной БД все офферы, которые мы когда-либо видели в этой кампании
    res = await db.execute(
        select(RemovedStreamOffer).where(RemovedStreamOffer.keitaro_campaign_id == campaign_id)
    )
    known_rows = res.scalars().all()
    known_by_stream: dict[int, set[int]] = {}
    for row in known_rows:
        known_by_stream.setdefault(row.stream_id, set()).add(row.offer_id)

    db_changed = False

    for stream in streams:
        sid = stream["id"]
        current_offers = stream.get("offers", [])
        active_ids = {int(o["offer_id"]) for o in current_offers}
        known_ids = known_by_stream.get(sid, set())

        # 1. Запоминаем в БД новые офферы, которые пришли из Keitaro (включая добавленные вручную в трекере)
        for oid in active_ids:
            if oid not in known_ids:
                db.add(
                    RemovedStreamOffer(
                        keitaro_campaign_id=campaign_id,
                        stream_id=sid,
                        offer_id=oid,
                    )
                )
                db_changed = True

        # 2. Все офферы, которые были в БД, но пропали в Keitaro (удалены у нас или вручную в Keitaro),
        #    подмешиваем в ответ как серые (disabled) с кнопкой BRING BACK
        for oid in known_ids:
            if oid not in active_ids:
                current_offers.append({
                    "offer_id": oid,
                    "offer_name": offers_map.get(oid, f"Offer #{oid}"),
                    "share": 0,
                    "state": "disabled",
                })

        stream["offers"] = current_offers

    if db_changed:
        await db.commit()

    return {
        "keitaro_url": settings.KEITARO_URL.rstrip("/"),
        "streams": streams,
    }


@app.put("/api/campaigns/{campaign_id}/streams/{stream_id}")
async def push_stream_to_kt(
    campaign_id: int,
    stream_id: int,
    payload: StreamOffersUpdate,
    db: AsyncSession = Depends(get_db),
):
    await keitaro_client.update_stream_offers(stream_id, payload.offers)

    # Убеждаемся, что все офферы потока (и активные, и disabled) записаны в историю локальной БД
    res = await db.execute(
        select(RemovedStreamOffer).where(
            RemovedStreamOffer.keitaro_campaign_id == campaign_id,
            RemovedStreamOffer.stream_id == stream_id,
        )
    )
    existing_ids = {r.offer_id for r in res.scalars().all()}

    for o in payload.offers:
        oid = int(o["offer_id"])
        if oid not in existing_ids:
            db.add(
                RemovedStreamOffer(
                    keitaro_campaign_id=campaign_id,
                    stream_id=stream_id,
                    offer_id=oid,
                )
            )

    db.add(
        StreamAuditLog(
            keitaro_campaign_id=campaign_id,
            stream_id=stream_id,
            action="PUSH_TO_KT",
            offer_id=len([o for o in payload.offers if o.get("state") != "disabled"]),
        )
    )
    await db.commit()

    return {"status": "ok"}