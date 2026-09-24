"""Community scam reports.

`ScamLocation` is a fixed gazetteer of approximate areas (city level). Reports
reference a location row instead of storing coordinates or addresses, so the
public scam map can only ever show city-level aggregates.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ScamLocation(Base):
    __tablename__ = "scam_locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    city: Mapped[str] = mapped_column(String(80))
    region: Mapped[str] = mapped_column(String(80), index=True)  # state / province
    country: Mapped[str] = mapped_column(String(64), default="India")
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)

    reports: Mapped[list[ScamReport]] = relationship(back_populates="location")


class ScamReport(Base):
    __tablename__ = "scam_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)  # SC-2026-00128
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)

    scam_type: Mapped[str] = mapped_column(String(32), index=True)
    description: Mapped[str] = mapped_column(Text)
    amount_lost: Mapped[float | None] = mapped_column(Float)
    location_id: Mapped[int | None] = mapped_column(ForeignKey("scam_locations.id"), index=True)
    analysis_id: Mapped[str | None] = mapped_column(ForeignKey("analyses.id", ondelete="SET NULL"))

    # Evidence image metadata only. The file itself is stored under a random name
    # outside any web-served directory and is never exposed via the public API.
    evidence_path: Mapped[str | None] = mapped_column(String(255))
    evidence_mime: Mapped[str | None] = mapped_column(String(32))

    client_id: Mapped[str | None] = mapped_column(String(64))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    location: Mapped[ScamLocation | None] = relationship(back_populates="reports", lazy="joined")
