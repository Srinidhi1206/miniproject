import type { ScamType } from "@/types/api";

export const SCAM_TYPE_LABEL: Record<ScamType, string> = {
  upi: "UPI / payment scam",
  job: "Job or task scam",
  phishing: "Phishing message",
  fake_website: "Fake website",
  qr: "QR code scam",
  call: "Call / impersonation",
  investment: "Investment scam",
  other: "Other",
};

export const SCAM_TYPES = Object.keys(SCAM_TYPE_LABEL) as ScamType[];
