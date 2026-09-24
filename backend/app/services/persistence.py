"""Persist analysis results (Analysis + AnalysisEvidence + ModelPrediction)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Analysis, AnalysisEvidence, ModelPrediction
from app.schemas.analysis import AnalysisResult, HistoryItem


def save_analysis(db: Session, result: AnalysisResult, client_id: str | None) -> Analysis:
    row = Analysis(
        id=result.id, created_at=result.created_at, client_id=client_id,
        input_type=result.input_type.value, channel=result.channel.value if result.channel else None,
        input_preview=result.input_preview, classification=result.classification.value,
        risk_score=result.risk_score, risk_level=result.risk_level.value, confidence=result.confidence,
        # The full extracted text is NOT stored — only the masked preview inside `result`.
        result=result.model_copy(update={"extracted": result.extracted.model_copy(update={"text": None})}).model_dump(mode="json"),
        duration_ms=result.duration_ms,
    )
    for comp in result.breakdown.components:
        for e in comp.evidence:
            row.evidence.append(AnalysisEvidence(source=e.source, code=e.code, label=e.label[:160],
                                                 severity=e.severity, weight=e.weight, detail=e.detail))
        if comp.model:
            row.predictions.append(ModelPrediction(model_name=comp.model.name, model_version=comp.model.version,
                                                   target=comp.model.target, probability=comp.model.probability,
                                                   label=comp.model.label))
    db.add(row)
    db.commit()
    return row


def _aware(dt: datetime) -> datetime:
    """SQLite drops tz info; everything SENTINEL stores is UTC."""
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def to_history_item(row: Analysis) -> HistoryItem:
    return HistoryItem(
        id=row.id, created_at=_aware(row.created_at), input_type=row.input_type, channel=row.channel,
        input_preview=row.input_preview, classification=row.classification,
        risk_score=row.risk_score, risk_level=row.risk_level,
    )
