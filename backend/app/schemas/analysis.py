"""Structured analysis contract shared by the agent, API and frontend."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class InputType(str, Enum):
    TEXT = "TEXT"
    URL = "URL"
    IMAGE = "IMAGE"
    QR = "QR"
    AUDIO = "AUDIO"


class Channel(str, Enum):
    sms = "sms"
    whatsapp = "whatsapp"
    email = "email"
    job_offer = "job_offer"
    social = "social"
    other = "other"


class Classification(str, Enum):
    SAFE = "SAFE"
    SUSPICIOUS = "SUSPICIOUS"
    SCAM = "SCAM"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


Severity = Literal["positive", "info", "low", "medium", "high", "critical"]


class Evidence(BaseModel):
    """One observable fact found by a deterministic rule, a model, or a decoder."""

    code: str
    label: str
    severity: Severity
    weight: int = Field(description="Points this evidence contributes to its component score (negative = reassuring).")
    source: str = Field(description="Which tool produced it, e.g. text_rules, url_rules, qr_decoder.")
    detail: str | None = None
    excerpt: str | None = Field(default=None, description="The exact snippet that triggered the rule, if any.")


class FeatureContribution(BaseModel):
    feature: str
    weight: float


class ModelOutput(BaseModel):
    name: str
    version: str
    target: Literal["text", "url"]
    probability: float = Field(ge=0, le=1, description="P(scam/phishing) from the model.")
    label: Literal["scam", "legit"]
    top_features: list[FeatureContribution] = []


class ComponentScore(BaseModel):
    """Score for one analyzed item (the message text, or one URL)."""

    component: Literal["text", "url", "upi"]
    subject: str
    score: int = Field(ge=0, le=100)
    model_points: float
    rule_points: int
    overrides: list[str] = []
    model: ModelOutput | None = None
    evidence: list[Evidence] = []


class RiskBreakdown(BaseModel):
    components: list[ComponentScore]
    base_score: int
    corroboration_bonus: int
    final_score: int
    formula: str


class ExtractedContent(BaseModel):
    text: str | None = None
    text_source: Literal["user", "ocr", "qr"] | None = None
    ocr_confidence: float | None = None
    qr_payload: str | None = None
    qr_payload_kind: Literal["url", "upi", "text", "wifi", "other"] | None = None
    upi: dict | None = None
    urls: list[str] = []


class Recommendation(BaseModel):
    id: str
    title: str
    detail: str
    priority: Literal["critical", "important", "general"]


class SourceRef(BaseModel):
    slug: str
    title: str
    section: str | None = None
    score: float | None = None


class Explanation(BaseModel):
    summary: str
    why_it_matters: list[str]
    sources: list[SourceRef] = []
    generated_by: str = Field(description="'template+rag' or 'llm:<model>+rag'")


class AgentStep(BaseModel):
    tool: str
    stage: Literal["validate", "extract", "analyze", "risk", "explain"]
    label: str
    status: Literal["done", "skipped", "failed"]
    duration_ms: int
    note: str | None = None


class AnalysisResult(BaseModel):
    id: str
    created_at: datetime
    input_type: InputType
    channel: Channel | None = None
    input_preview: str

    classification: Classification
    verdict: str
    risk_score: int = Field(ge=0, le=100)
    risk_level: RiskLevel
    confidence: float = Field(ge=0, le=1, description="Confidence of the primary model in its own label.")

    findings: list[Evidence]
    reassurances: list[Evidence]
    recommendations: list[Recommendation]
    explanation: Explanation
    extracted: ExtractedContent
    breakdown: RiskBreakdown
    trace: list[AgentStep]
    limitations: list[str] = []
    duration_ms: int = 0


# ---- Request bodies ----------------------------------------------------------

class TextAnalyzeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20_000)
    channel: Channel = Channel.sms


class UrlAnalyzeRequest(BaseModel):
    url: str = Field(min_length=1, max_length=4096)


class HistoryItem(BaseModel):
    id: str
    created_at: datetime
    input_type: InputType
    channel: Channel | None
    input_preview: str
    classification: Classification
    risk_score: int
    risk_level: RiskLevel


class HistoryPage(BaseModel):
    items: list[HistoryItem]
    total: int


class ClientStats(BaseModel):
    total_scans: int
    threats_detected: int
    suspicious: int
    safe: int
    scans_today: int
    by_type: dict[str, int]
    last_scan_at: datetime | None
