import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import SettingsPage from "@/app/(app)/settings/page";

describe("Settings — privacy & protection", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    try { window.localStorage.clear(); } catch { /* ignore */ }
  });

  it("shows the privacy information and controls", () => {
    render(<SettingsPage />);
    expect(screen.getByRole("heading", { name: "Privacy & protection" })).toBeInTheDocument();
    expect(screen.getByText(/isn't linked to your name, phone number or email/i)).toBeInTheDocument();
    for (const term of ["Anonymous device ID", "What we keep", "What we don't keep"]) {
      expect(screen.getByText(term)).toBeInTheDocument();
    }
    expect(screen.getByRole("button", { name: /start a new anonymous id/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /manage or clear history/i })).toHaveAttribute("href", "/history");
  });

  it("has no protection-status card and makes no backend request", () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    const { container } = render(<SettingsPage />);
    expect(screen.queryByText(/protection status/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/can't be reached/i)).not.toBeInTheDocument();
    expect(container.textContent).not.toMatch(/Active|coming soon/);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("creates a new anonymous ID on request", () => {
    render(<SettingsPage />);
    const before = window.localStorage.getItem("sentinel.device-id");
    fireEvent.click(screen.getByRole("button", { name: /start a new anonymous id/i }));
    const after = window.localStorage.getItem("sentinel.device-id");
    expect(after).toMatch(/^[A-Za-z0-9-]{8,64}$/);
    expect(after).not.toBe(before);
    expect(screen.getByText(after!)).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(/new anonymous ID/i);
  });
});
