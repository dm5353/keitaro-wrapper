import uuid
import httpx
from fastapi import HTTPException

from app.config import settings
from app.schemas import CampaignCreate


class KeitaroClient:
    def __init__(self):
        self.base_url = settings.KEITARO_URL.rstrip("/")
        self.headers = {
            "Api-Key": settings.KEITARO_API_KEY,
            "Content-Type": "application/json",
        }

    async def _request(self, method: str, path: str, json: dict | None = None):
        url = f"{self.base_url}/admin_api/v1{path}"
        timeout = httpx.Timeout(60.0, connect=20.0)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(method, url, headers=self.headers, json=json)
        except httpx.TimeoutException as exc:
            raise HTTPException(
                status_code=504,
                detail=f"Таймаут при обращении к Keitaro ({method} {path}): {type(exc).__name__}",
            )

        if response.status_code >= 400:
            raise HTTPException(
                status_code=502,
                detail=f"Ошибка Keitaro API ({response.status_code}): {response.text}",
            )
        return response.json()

    async def get_offers(self, search: str = "") -> list[dict]:
        offers = await self._request("GET", "/offers")
        if not search:
            return [{"id": o["id"], "name": o["name"]} for o in offers[:100]]
        q = search.lower()
        return [
            {"id": o["id"], "name": o["name"]}
            for o in offers
            if q in str(o["id"]) or q in o["name"].lower()
        ][:30]

    async def get_defaults(self) -> dict:
        domains = await self._request("GET", "/domains")
        groups = await self._request("GET", "/groups?type=campaigns")
        sources = await self._request("GET", "/traffic_sources")
        return {
            "domain_id": domains[0]["id"] if domains else None,
            "group_id": groups[0]["id"] if groups else None,
            "traffic_source_id": sources[0]["id"] if sources else None,
            "domains": domains,
            "groups": groups,
            "sources": sources,
        }

    async def create_campaign_with_streams(self, data: CampaignCreate) -> dict:
        if not (data.domain_id and data.group_id and data.traffic_source_id):
            defaults = await self.get_defaults()
        else:
            defaults = {}

        countries = data.parsed_countries()

        # 1. Создание кампании
        campaign_body = {
            "name": data.name,
            "alias": f"c-{uuid.uuid4().hex[:8]}",
            "domain_id": data.domain_id or defaults.get("domain_id"),
            "group_id": data.group_id or defaults.get("group_id"),
            "traffic_source_id": data.traffic_source_id or defaults.get("traffic_source_id"),
            "state": "active",
        }
        campaign = await self._request("POST", "/campaigns", json=campaign_body)
        campaign_id = campaign["id"]

        try:
            # 2. Поток 1: Перехват указанных стран -> редирект на Google
            stream_1 = {
                "campaign_id": campaign_id,
                "type": "regular",
                "name": "Geo -> Google",
                "position": 1,
                "schema": "redirect",
                "action_type": "http",
                "action_options": {"url": "https://google.com"},
                "filters": [
                    {
                        "name": "country",
                        "mode": "accept",
                        "payload": countries,
                    }
                ],
                "state": "active",
            }
            await self._request("POST", "/streams", json=stream_1)

            # 3. Поток 2: Весь остальной трафик -> выбранный оффер
            stream_2 = {
                "campaign_id": campaign_id,
                "type": "regular",
                "name": "Default -> Offer",
                "position": 2,
                "schema": "landings",
                "action_type": "campaign",
                "offers": [
                    {
                        "offer_id": data.offer_id,
                        "share": 100,
                        "state": "active",
                    }
                ],
                "state": "active",
            }
            await self._request("POST", "/streams", json=stream_2)
        except Exception as exc:
            # Откат: переименовываем (чтобы не блокировать имя в архиве) и удаляем кампанию
            try:
                await self._request(
                    "PUT",
                    f"/campaigns/{campaign_id}",
                    json={"name": f"{data.name}_deleted_{uuid.uuid4().hex[:6]}"},
                )
            except Exception:
                pass
            await self._request("DELETE", f"/campaigns/{campaign_id}")
            raise exc

        return campaign

    async def get_campaign_streams(self, campaign_id: int) -> list[dict]:
        """Получает потоки кампании и подтягивает названия офферов."""
        streams = await self._request("GET", f"/campaigns/{campaign_id}/streams")
        offers_list = await self._request("GET", "/offers")
        offers_map = {o["id"]: o["name"] for o in offers_list}

        for stream in streams:
            for item in stream.get("offers", []):
                oid = item.get("offer_id")
                item["offer_name"] = offers_map.get(oid, f"Offer #{oid}")
        return streams

    async def update_stream_offers(self, stream_id: int, offers: list[dict]) -> dict:
        """Отправляет в Keitaro только активные офферы (удалённые пропадают из трекера)."""
        clean_offers = [
            {
                "offer_id": int(o["offer_id"]),
                "share": int(o["share"]),
                "state": "active",
            }
            for o in offers
            if o.get("state", "active") != "disabled"
        ]
        return await self._request("PUT", f"/streams/{stream_id}", json={"offers": clean_offers})




keitaro_client = KeitaroClient()