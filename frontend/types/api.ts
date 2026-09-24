// Mirrors backend/app/schemas/*.py — keep in sync.

export type InputType = "TEXT" | "URL" | "IMAGE" | "QR" | "AUDIO";
export type Channel = "sms" | "whatsapp" | "email" | "job_offer" | "social" | "other";
export type Classification = "SAFE" | "SUSPICIOUS" | "SCAM";
export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type Severity = "positive" | "info" | "low" | "medium" | "high" | "critical";
export type Stage = "validate" | "extract" | "analyze" | "risk" | "explain";

export interface Evidence {
  code: string;
  label: string;
  severity: Severity;
  weight: number;
  source: string;
  detail?: string | null;
  excerpt?: string | null;
}

export interface FeatureContribution {
  feature: string;
  weight: number;
}

export interface ModelOutput {
  name: string;
  version: string;
  target: "text" | "url";
  probability: number;
  label: "scam" | "legit";
  top_features: FeatureContribution[];
}

export interface ComponentScore {
  component: "text" | "url" | "upi";
  subject: string;
  score: number;
  model_points: number;
  rule_points: number;
  overrides: string[];
  model?: ModelOutput | null;
  evidence: Evidence[];
}

export interface RiskBreakdown {
  components: ComponentScore[];
  base_score: number;
  corroboration_bonus: number;
  final_score: number;
  formula: string;
}

export interface ExtractedContent {
  text?: string | null;
  text_source?: "user" | "ocr" | "qr" | null;
  ocr_confidence?: number | null;
  qr_payload?: string | null;
  qr_payload_kind?: "url" | "upi" | "text" | "wifi" | "other" | null;
  upi?: {
    payee_vpa?: string | null;
    payee_name?: string | null;
    amount?: number | null;
    currency?: string;
    note?: string | null;
    merchant_code?: string | null;
  } | null;
  urls: string[];
}

export interface Recommendation {
  id: string;
  title: string;
  detail: string;
  priority: "critical" | "important" | "general";
}

export interface SourceRef {
  slug: string;
  title: string;
  section?: string | null;
  score?: number | null;
}

export interface Explanation {
  summary: string;
  why_it_matters: string[];
  sources: SourceRef[];
  generated_by: string;
}

export interface AgentStep {
  tool: string;
  stage: Stage;
  label: string;
  status: "done" | "skipped" | "failed";
  duration_ms: number;
  note?: string | null;
}

export interface AnalysisResult {
  id: string;
  created_at: string;
  input_type: InputType;
  channel?: Channel | null;
  input_preview: string;
  classification: Classification;
  verdict: string;
  risk_score: number;
  risk_level: RiskLevel;
  confidence: number;
  findings: Evidence[];
  reassurances: Evidence[];
  recommendations: Recommendation[];
  explanation: Explanation;
  extracted: ExtractedContent;
  breakdown: RiskBreakdown;
  trace: AgentStep[];
  limitations: string[];
  duration_ms: number;
}

export type StreamEvent =
  | { type: "stage"; stage: Stage }
  | { type: "step"; step: AgentStep }
  | { type: "result"; result: AnalysisResult }
  | { type: "error"; status: number; error: ApiErrorBody };

export interface ApiErrorBody {
  code: string;
  message: string;
  hint?: string;
  fields?: string[];
}

export interface HistoryItem {
  id: string;
  created_at: string;
  input_type: InputType;
  channel?: Channel | null;
  input_preview: string;
  classification: Classification;
  risk_score: number;
  risk_level: RiskLevel;
}

export interface HistoryPage {
  items: HistoryItem[];
  total: number;
}

export interface ClientStats {
  total_scans: number;
  threats_detected: number;
  suspicious: number;
  safe: number;
  scans_today: number;
  by_type: Record<string, number>;
  last_scan_at?: string | null;
}

export type ScamType = "upi" | "job" | "phishing" | "fake_website" | "qr" | "call" | "investment" | "other";

export interface ReportOptions {
  scam_types: { value: ScamType; label: string }[];
  locations: { slug: string; city: string; region: string }[];
  max_description: number;
  max_upload_mb: number;
}

export interface ReportReceipt {
  report_id: string;
  created_at: string;
  scam_type: ScamType;
  location?: string | null;
  evidence_attached: boolean;
  next_steps: string[];
}

export interface MapLocation {
  slug: string;
  city: string;
  region: string;
  lat: number;
  lng: number;
  total: number;
  by_type: Partial<Record<ScamType, number>>;
}

export interface ScamMapData {
  locations: MapLocation[];
  totals_by_type: Partial<Record<ScamType, number>>;
  total_reports: number;
  demo_reports: number;
  community_reports: number;
  regions: string[];
  days: number;
  generated_at: string;
}

export interface GuideSummary {
  slug: string;
  title: string;
  category: string;
  summary: string;
  read_minutes: number;
  tags: string[];
}

export interface GuideDetail extends GuideSummary {
  body_markdown: string;
}

export interface HealthCapability {
  status: string;
  [key: string]: unknown;
}

export interface Health {
  status: string;
  database: { status: string; dialect: string };
  environment: string;
  capabilities: Record<string, HealthCapability>;
}
