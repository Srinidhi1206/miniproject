"""Analysis persistence.

Privacy note: for anonymous users we store a short *preview* of the submitted
content (digits masked) rather than the full raw text, plus the structured
result. `client_id` is a random device identifier generated in the browser —
it is not tied to any personal identity. `user_id` is reserved for the
optional account system (future phase) and is always NULL today.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    client_id: Mapped[str | None] = mapped_column(String(64), index=True)
    user_id: Mapped[str | None] = mapped_column(String(64), index=True)  # reserved for auth phase

    input_type: Mapped[str] = mapped_column(String(16))  # TEXT | URL | IMAGE | QR | AUDIO
    channel: Mapped[str | None] = mapped_column(String(24))  # sms | whatsapp | email | job_offer | ...
    input_preview: Mapped[str] = mapped_column(Text, default="")

    classification: Mapped[str] = mapped_column(String(16))  # SAFE | SUSPICIOUS | SCAM
    risk_score: Mapped[int] = mapped_column(Integer)
    risk_level: Mapped[str] = mapped_column(String(16))  # LOW | MEDIUM | HIGH | CRITICAL
    confidence: Mapped[float] = mapped_column(Float)

    result: Mapped[dict] = mapped_column(JSON)  # full structured AnalysisResult
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)

    evidence: Mapped[list[AnalysisEvidence]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan", lazy="selectin")
    predictions: Mapped[list[ModelPrediction]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan", lazy="selectin")


class AnalysisEvidence(Base):
    __tablename__ = "analysis_evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), index=True)
    source: Mapped[str] = mapped_column(String(32))  # text_rules | url_rules | qr | ocr | reputation ...
    code: Mapped[str] = mapped_column(String(48))
    label: Mapped[str] = mapped_column(String(160))
    severity: Mapped[str] = mapped_column(String(12))
    weight: Mapped[int] = mapped_column(Integer)
    detail: Mapped[str | None] = mapped_column(Text)

    analysis: Mapped[Analysis] = relationship(back_populates="evidence")


class ModelPrediction(Base):
    """Raw output of each ML model call — kept for auditing and model evaluation."""

    __tablename__ = "model_predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), index=True)
    model_name: Mapped[str] = mapped_column(String(64))
    model_version: Mapped[str] = mapped_column(String(32))
    target: Mapped[str] = mapped_column(String(16))  # text | url
    probability: Mapped[float] = mapped_column(Float)
    label: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    analysis: Mapped[Analysis] = relationship(back_populates="predictions")
