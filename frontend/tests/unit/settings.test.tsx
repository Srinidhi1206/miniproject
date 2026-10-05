import { render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Health } from "@/types/api";

const health = vi.fn<() => Promise<Health>>();
vi.mock("@/lib/api", () => ({ api: { health: () => health() } }));

import SettingsPage from "@/app/(app)/settings/page";

const READY = (extra: Record<string, unknown> = {}) => ({ status: "ready", ...extra });

function liveHealth(overrides: Partial<Health["capabilities"]> = {}): Health {
  return {
    status: "ok",
    environment: "production",
    database: { status: "ready", dialect: "postgresql" },
    capabilities: {
      text_model: READY({ name: "tfidf-logreg", version: "20260924.1347", holdout_f1: 0.9495, holdout_roc_auc: 0.9905 }),
      url_model: READY({ name: "domain-charngram-logreg", version: "20260924.1315", holdout_roc_auc: 0.808 }),
      ocr: READY({ engine: "rapidocr-onnx" }),
      qr_decoder: READY({ engine: "opencv" }),
      rag: READY({ chunks: 51, backend: "faiss", embedder: "lsa-tfidf-svd" }),
      llm_explanations: { status: "disabled", note: "Grounded template explanations are used" },
      url_reputation: READY(),
      audio: { status: "unavailable", note: "Voice analysis is planned for Phase 2" },
      voice_authenticity: { status: "unavailable" },
      ...overrides,
    },
  };
}

describe("Settings — user-facing protection status", () => {
  beforeEach(() => health.mockReset());

  it("shows plain-language protections derived from the live health check", async () => {
    health.mockResolvedValue(liveHealth());
    render(<SettingsPage />);
    const list = await screen.findByRole("list");
    for (const label of ["Scam message detection", "Suspicious link checking", "Screenshot & QR scanning",
      "Safety guidance", "Live link reputation checking", "Secure anonymous history"]) {
      expect(within(list).getByText(label)).toBeInTheDocument();
    }
    expect(within(list).getAllByText("Active")).toHaveLength(6);
  });

  it("never exposes model metrics, versions, engines, the database or internal features", async () => {
    health.mockResolvedValue(liveHealth());
    const { container } = render(<SettingsPage />);
    await screen.findByText("Scam message detection");
    const text = container.textContent ?? "";
    for (const hidden of ["F1", "ROC", "20260924", "tfidf", "rapidocr", "opencv", "faiss", "PostgreSQL", "postgresql",
      "LLM", "Deepfake", "UNAVAILABLE", "Phase 2", "passages"]) {
      expect(text).not.toContain(hidden);
    }
    expect(screen.getByText(/more protection features/i)).toBeInTheDocument();
  });

  it("does not claim link reputation checking when it isn't configured", async () => {
    health.mockResolvedValue(liveHealth({ url_reputation: { status: "not_configured" } }));
    render(<SettingsPage />);
    await screen.findByText("Scam message detection");
    expect(screen.queryByText("Live link reputation checking")).not.toBeInTheDocument();
  });

  it("reports degraded capabilities honestly instead of 'Active'", async () => {
    health.mockResolvedValue(liveHealth({ text_model: { status: "unavailable" }, ocr: { status: "unavailable" } }));
    render(<SettingsPage />);
    const row = (await screen.findByText("Scam message detection")).closest("li")!;
    expect(within(row).getByText("Limited")).toBeInTheDocument();
    const scan = screen.getByText("Screenshot & QR scanning").closest("li")!;
    expect(within(scan).getByText("Limited")).toBeInTheDocument();
  });

  it("keeps the privacy controls", async () => {
    health.mockResolvedValue(liveHealth());
    render(<SettingsPage />);
    expect(screen.getByRole("button", { name: /start a new anonymous id/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /clear history/i })).toHaveAttribute("href", "/history");
    expect(screen.getByText(/isn't linked to your name, phone number or email/i)).toBeInTheDocument();
  });
});
