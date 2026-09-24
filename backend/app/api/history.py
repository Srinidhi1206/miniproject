"""Analysis retrieval, per-device history and statistics."""

from __future__ import annotations

from datetime import datetime, time, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, delete, func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import required_client_id
from app.core.errors import not_found
from app.db.session import get_db
from app.models import Analysis
from app.schemas.analysis import AnalysisResult, ClientStats, HistoryPage
from app.services.persistence import to_history_item

router = APIRouter(prefix="/api", tags=["history"])


@router.get("/analysis/{analysis_id}", response_model=AnalysisResult, summary="Fetch a stored analysis report")
def get_analysis(analysis_id: str, db: Session = Depends(get_db)):
    # Ids are random 128-bit values, so knowing the id is the capability to view the report
    # (like an unlisted link). Only masked previews are stored.
    if not analysis_id.isalnum() or len(analysis_id) > 32:
        raise not_found("analysis")
    row = db.get(Analysis, analysis_id)
    if row is None:
        raise not_found("analysis")
    return AnalysisResult.model_validate(row.result)


@router.get("/history", response_model=HistoryPage, summary="This device's analyses")
def history(
    client_id: str = Depends(required_client_id), db: Session = Depends(get_db),
    q: str | None = Query(None, max_length=100), input_type: str | None = Query(None, alias="type"),
    level: str | None = None,
    sort: Literal["newest", "oldest", "risk_desc", "risk_asc"] = "newest",
    limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
):
    stmt = select(Analysis).where(Analysis.client_id == client_id)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Analysis.input_preview.ilike(like), Analysis.classification.ilike(like)))
    if input_type:
        stmt = stmt.where(Analysis.input_type == input_type.upper())
    if level:
        stmt = stmt.where(Analysis.risk_level == level.upper())
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    order = {"newest": Analysis.created_at.desc(), "oldest": Analysis.created_at.asc(),
             "risk_desc": Analysis.risk_score.desc(), "risk_asc": Analysis.risk_score.asc()}[sort]
    rows = db.scalars(stmt.order_by(order).limit(limit).offset(offset)).all()
    return HistoryPage(items=[to_history_item(r) for r in rows], total=total)


@router.delete("/history", status_code=204, summary="Delete all of this device's analyses")
def clear_history(client_id: str = Depends(required_client_id), db: Session = Depends(get_db)):
    db.execute(delete(Analysis).where(Analysis.client_id == client_id))
    db.commit()


@router.get("/stats", response_model=ClientStats, summary="Statistics for this device's analyses")
def stats(client_id: str = Depends(required_client_id), db: Session = Depends(get_db)):
    base = select(Analysis).where(Analysis.client_id == client_id).subquery()
    today = datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)
    row = db.execute(select(
        func.count(),
        func.sum(case((base.c.classification == "SCAM", 1), else_=0)),
        func.sum(case((base.c.classification == "SUSPICIOUS", 1), else_=0)),
        func.sum(case((base.c.classification == "SAFE", 1), else_=0)),
        func.sum(case((base.c.created_at >= today, 1), else_=0)),
        func.max(base.c.created_at),
    )).one()
    by_type = dict(db.execute(select(base.c.input_type, func.count()).group_by(base.c.input_type)).all())
    last = row[5]
    if last is not None and last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return ClientStats(total_scans=row[0] or 0, threats_detected=row[1] or 0, suspicious=row[2] or 0,
                       safe=row[3] or 0, scans_today=row[4] or 0, by_type=by_type, last_scan_at=last)
