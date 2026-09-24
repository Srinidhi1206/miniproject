"""Community features: scam reports, the anonymised scam map, safety guides."""

from __future__ import annotations

import io
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import optional_client_id
from app.core.config import get_settings
from app.core.errors import SentinelError, not_found
from app.core.ratelimit import rate_limit
from app.core.security import clean_text, load_image, read_upload
from app.db.session import get_db
from app.models import Analysis, SafetyGuide, ScamLocation, ScamReport
from app.schemas.community import (
    SCAM_TYPE_LABELS, GuideDetail, GuideSummary, LocationOption, MapLocation, ReportOptions, ReportReceipt,
    ScamMap, ScamType,
)

router = APIRouter(prefix="/api", tags=["community"])
MAX_DESCRIPTION = 2000


@router.get("/reports/options", response_model=ReportOptions, summary="Scam categories and approximate locations")
def report_options(db: Session = Depends(get_db)):
    locs = db.scalars(select(ScamLocation).order_by(ScamLocation.city)).all()
    return ReportOptions(
        scam_types=[{"value": t.value, "label": SCAM_TYPE_LABELS[t]} for t in ScamType],
        locations=[LocationOption(slug=l.slug, city=l.city, region=l.region) for l in locs],
        max_description=MAX_DESCRIPTION, max_upload_mb=get_settings().max_upload_mb,
    )


def _store_evidence(data: bytes) -> tuple[str, str]:
    """Re-encode the image (strips EXIF/GPS metadata and any trailing payload) under a random name."""
    image = load_image(data)
    image.thumbnail((2000, 2000))
    folder = get_settings().var_dir / "uploads" / "reports"
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.png"
    buf = io.BytesIO()
    image.save(buf, format="PNG", optimize=True)
    (folder / name).write_bytes(buf.getvalue())
    return f"reports/{name}", "image/png"


@router.post("/reports", response_model=ReportReceipt, status_code=201, dependencies=[Depends(rate_limit)],
             summary="Submit a scam report")
async def create_report(
    scam_type: ScamType = Form(...),
    description: str = Form(..., min_length=10, max_length=MAX_DESCRIPTION * 2),
    amount_lost: float | None = Form(None, ge=0, le=1e9),
    location: str | None = Form(None, max_length=64),
    analysis_id: str | None = Form(None, max_length=32),
    evidence: UploadFile | None = File(None),
    client_id: str | None = Depends(optional_client_id),
    db: Session = Depends(get_db),
):
    desc = clean_text(description)
    if len(desc) < 10:
        raise SentinelError("TEXT_TOO_SHORT", "Please describe what happened in a sentence or two.", 400)
    if len(desc) > MAX_DESCRIPTION:
        raise SentinelError("TEXT_TOO_LONG", f"Please keep the description under {MAX_DESCRIPTION} characters.", 413)

    loc = None
    if location:
        loc = db.scalar(select(ScamLocation).where(ScamLocation.slug == location))
        if loc is None:
            raise SentinelError("INVALID_LOCATION", "Please pick a location from the list.", 400)
    if analysis_id and (not analysis_id.isalnum() or db.get(Analysis, analysis_id) is None):
        analysis_id = None

    evidence_path = evidence_mime = None
    if evidence is not None and evidence.filename:
        evidence_path, evidence_mime = _store_evidence(await read_upload(evidence))

    report = ScamReport(public_id="pending", scam_type=scam_type.value, description=desc,
                        amount_lost=amount_lost, location_id=loc.id if loc else None, analysis_id=analysis_id,
                        evidence_path=evidence_path, evidence_mime=evidence_mime, client_id=client_id, is_demo=False)
    db.add(report)
    db.flush()
    report.public_id = f"SC-{report.created_at.year}-{report.id:05d}"
    db.commit()
    return ReportReceipt(
        report_id=report.public_id, created_at=report.created_at, scam_type=scam_type,
        location=f"{loc.city}, {loc.region}" if loc else None, evidence_attached=evidence_path is not None,
        next_steps=[
            "If you lost money, call the national cybercrime helpline 1930 now — speed matters for recovery.",
            "File an official complaint at cybercrime.gov.in and quote this report ID in your notes.",
            "Tell your bank to block cards/UPI and dispute the transaction.",
        ],
    )


@router.get("/scam-map", response_model=ScamMap, summary="Aggregated, anonymised scam reports by city")
def scam_map(
    db: Session = Depends(get_db),
    scam_type: ScamType | None = Query(None, alias="type"),
    region: str | None = Query(None, max_length=80),
    days: int = Query(90, ge=1, le=3650),
    include_demo: bool = True,
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    filters = [ScamReport.created_at >= since, ScamReport.location_id.is_not(None)]
    if scam_type:
        filters.append(ScamReport.scam_type == scam_type.value)
    if region:
        filters.append(ScamLocation.region == region)
    if not include_demo:
        filters.append(ScamReport.is_demo.is_(False))

    rows = db.execute(
        select(ScamLocation, ScamReport.scam_type, func.count(ScamReport.id))
        .join(ScamReport, ScamReport.location_id == ScamLocation.id)
        .where(*filters).group_by(ScamLocation.id, ScamReport.scam_type)
    ).all()
    by_loc: dict[int, MapLocation] = {}
    totals: dict[str, int] = {}
    for loc, stype, n in rows:
        m = by_loc.setdefault(loc.id, MapLocation(slug=loc.slug, city=loc.city, region=loc.region,
                                                  lat=loc.lat, lng=loc.lng, total=0, by_type={}))
        m.by_type[stype] = n
        m.total += n
        totals[stype] = totals.get(stype, 0) + n

    demo_count = db.scalar(select(func.count(ScamReport.id)).select_from(ScamReport)
                           .join(ScamLocation, ScamReport.location_id == ScamLocation.id)
                           .where(*filters, ScamReport.is_demo.is_(True))) or 0
    total = sum(totals.values())
    regions = sorted(r for (r,) in db.execute(select(ScamLocation.region).distinct()).all())
    return ScamMap(locations=sorted(by_loc.values(), key=lambda m: -m.total), totals_by_type=totals,
                   total_reports=total, demo_reports=demo_count, community_reports=total - demo_count,
                   regions=regions, days=days, generated_at=datetime.now(timezone.utc))


@router.get("/safety-guides", response_model=list[GuideSummary], summary="Safety Center guides")
def list_guides(category: str | None = None, db: Session = Depends(get_db)):
    stmt = select(SafetyGuide).order_by(SafetyGuide.order)
    if category:
        stmt = stmt.where(SafetyGuide.category == category)
    return [GuideSummary(slug=g.slug, title=g.title, category=g.category, summary=g.summary,
                         read_minutes=g.read_minutes, tags=g.tags or []) for g in db.scalars(stmt).all()]


@router.get("/safety-guides/{slug}", response_model=GuideDetail, summary="One Safety Center guide")
def get_guide(slug: str, db: Session = Depends(get_db)):
    g = db.scalar(select(SafetyGuide).where(SafetyGuide.slug == slug))
    if g is None:
        raise not_found("guide")
    return GuideDetail(slug=g.slug, title=g.title, category=g.category, summary=g.summary,
                       read_minutes=g.read_minutes, tags=g.tags or [], body_markdown=g.body_markdown)
