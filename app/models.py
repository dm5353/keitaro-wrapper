from datetime import datetime
from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class CampaignLog(Base):
    __tablename__ = "campaign_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    keitaro_campaign_id: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    geo: Mapped[str] = mapped_column(String(255), nullable=False)
    offer_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class StreamAuditLog(Base):
    __tablename__ = "stream_audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    keitaro_campaign_id: Mapped[int] = mapped_column(Integer, nullable=False)
    stream_id: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # ADD или REMOVE
    offer_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class RemovedStreamOffer(Base):
    __tablename__ = "removed_stream_offers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    keitaro_campaign_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    stream_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    offer_id: Mapped[int] = mapped_column(Integer, nullable=False)
