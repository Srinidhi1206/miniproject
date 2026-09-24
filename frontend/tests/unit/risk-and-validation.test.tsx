import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RiskBadge, ScoreMeter } from "@/components/risk/risk-badge";
import { validateImageFile } from "@/features/scanner/dropzone";
import { levelFor, RISK } from "@/lib/risk";

describe("risk bands", () => {
  it("match the backend thresholds", () => {
    expect([0, 29, 30, 59, 60, 79, 80, 100].map(levelFor)).toEqual([
      "LOW", "LOW", "MEDIUM", "MEDIUM", "HIGH", "HIGH", "CRITICAL", "CRITICAL",
    ]);
  });

  it("badges always carry a text label, never colour alone", () => {
    render(<RiskBadge level="CRITICAL" score={91} />);
    expect(screen.getByText(RISK.CRITICAL.short)).toBeInTheDocument();
    expect(screen.getByText(/91/)).toBeInTheDocument();
  });

  it("score meter exposes an accessible value", () => {
    render(<ScoreMeter score={72} />);
    const meter = screen.getByRole("meter", { name: /risk score/i });
    expect(meter).toHaveAttribute("aria-valuenow", "72");
  });
});

describe("client-side upload validation", () => {
  const file = (type: string, size: number) => new File([new Uint8Array(size)], "f", { type });

  it("accepts common screenshot formats", () => {
    expect(validateImageFile(file("image/png", 1000))).toBeNull();
    expect(validateImageFile(file("image/jpeg", 1000))).toBeNull();
  });

  it("rejects other types with a friendly message", () => {
    expect(validateImageFile(file("application/pdf", 1000))).toMatch(/isn't supported/);
    expect(validateImageFile(file("image/svg+xml", 1000))).toMatch(/isn't supported/);
  });

  it("rejects files over the limit and empty files", () => {
    expect(validateImageFile(file("image/png", 9 * 1024 * 1024))).toMatch(/limit is 8 MB/);
    expect(validateImageFile(file("image/png", 0))).toMatch(/empty/);
  });
});
