from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class ScamType(str, Enum):
    upi = "upi"
    job = "job"
    phishing = "phishing"
    fake_website = "fake_website"
    qr = "qr"
    call = "call"
    investment = "investment"
    other = "other"


SCAM_TYPE_LABELS = {
    ScamType.upi: "UPI / payment scam", ScamType.job: "Job or task scam", ScamType.phishing: "Phishing message",
    ScamType.fake_website: "Fake website", ScamType.qr: "QR code scam", ScamType.call: "Call / impersonation scam",
    ScamType.investment: "Investment scam", ScamType.other: "Other",
}


class LocationOption(BaseModel):
    slug: str
    city: str
    region: str


class ReportOptions(BaseModel):
    scam_types: list[dict]
    locations: list[LocationOption]
    max_description: int
    max_upload_mb: int


class ReportReceipt(BaseModel):
    report_id: str
    created_at: datetime
    scam_type: ScamType
    location: str | None
    evidence_attached: bool
    next_steps: list[str]


class MapLocation(BaseModel):
    slug: str
    city: str
    region: str
    lat: float
    lng: float
    total: int
    by_type: dict[str, int]


class ScamMap(BaseModel):
    locations: list[MapLocation]
    totals_by_type: dict[str, int]
    total_reports: int
    demo_reports: int
    community_reports: int
    regions: list[str]
    days: int
    generated_at: datetime


class GuideSummary(BaseModel):
    slug: str
    title: str
    category: str
    summary: str
    read_minutes: int
    tags: list[str]


class GuideDetail(GuideSummary):
    body_markdown: str
