import type { Classification, InputType, RiskLevel, Severity, Stage } from "@/types/api";

/** Risk is always communicated with words AND colour, never colour alone. */
export const RISK: Record<RiskLevel, { label: string; short: string; text: string; bg: string; line: string; solid: string; range: string }> = {
  LOW: { label: "Low risk", short: "Low", text: "text-safe", bg: "bg-safe-bg", line: "border-safe-line", solid: "bg-safe", range: "0–29" },
  MEDIUM: { label: "Medium risk", short: "Medium", text: "text-warn", bg: "bg-warn-bg", line: "border-warn-line", solid: "bg-warn", range: "30–59" },
  HIGH: { label: "High risk", short: "High", text: "text-high", bg: "bg-high-bg", line: "border-high-line", solid: "bg-high", range: "60–79" },
  CRITICAL: { label: "Critical risk", short: "Critical", text: "text-critical", bg: "bg-critical-bg", line: "border-critical-line", solid: "bg-critical", range: "80–100" },
};

export const CLASSIFICATION_LABEL: Record<Classification, string> = {
  SAFE: "Likely safe",
  SUSPICIOUS: "Suspicious",
  SCAM: "Potential scam",
};

export const SEVERITY: Record<Severity, { label: string; text: string; bg: string; dot: string }> = {
  critical: { label: "Critical", text: "text-critical", bg: "bg-critical-bg", dot: "bg-critical" },
  high: { label: "High", text: "text-high", bg: "bg-high-bg", dot: "bg-high" },
  medium: { label: "Medium", text: "text-warn", bg: "bg-warn-bg", dot: "bg-warn" },
  low: { label: "Low", text: "text-muted", bg: "bg-paper-2", dot: "bg-faint" },
  info: { label: "Info", text: "text-ink-2", bg: "bg-paper-2", dot: "bg-ink-2" },
  positive: { label: "Reassuring", text: "text-safe", bg: "bg-safe-bg", dot: "bg-safe" },
};

export const INPUT_LABEL: Record<InputType, string> = {
  TEXT: "Message",
  URL: "Link",
  IMAGE: "Screenshot",
  QR: "QR code",
  AUDIO: "Voice",
};

export const STAGES: { id: Stage; label: string }[] = [
  { id: "validate", label: "Analyzing input" },
  { id: "extract", label: "Extracting content" },
  { id: "analyze", label: "Checking suspicious indicators" },
  { id: "risk", label: "Assessing risk" },
  { id: "explain", label: "Preparing explanation" },
];

export function levelFor(score: number): RiskLevel {
  if (score >= 80) return "CRITICAL";
  if (score >= 60) return "HIGH";
  if (score >= 30) return "MEDIUM";
  return "LOW";
}
