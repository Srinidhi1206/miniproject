import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

import { Scanner } from "@/features/scanner/scanner";

describe("Scanner", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("offers every input type, with voice honestly marked as not yet available", () => {
    render(<Scanner />);
    for (const name of ["Message", "Link", "Screenshot", "QR code"]) {
      expect(screen.getByRole("tab", { name: new RegExp(name) })).toBeInTheDocument();
    }
    expect(screen.getByRole("tab", { name: /Voice/ })).toHaveTextContent(/Soon/i);
  });

  it("validates an empty message without calling the API", () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    render(<Scanner />);
    fireEvent.click(screen.getByRole("button", { name: /Analyze message/i }));
    expect(screen.getByRole("alert")).toHaveTextContent(/Paste the message/);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("shows the voice capability notice instead of a fake analyser", () => {
    render(<Scanner initialMode="voice" />);
    expect(screen.getByText(/isn't available in the current version/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Analyze/ })).not.toBeInTheDocument();
  });

  it("lets people pick the message source", () => {
    render(<Scanner />);
    const whatsapp = screen.getByRole("radio", { name: "WhatsApp" });
    fireEvent.click(whatsapp);
    expect(whatsapp).toHaveAttribute("aria-checked", "true");
    expect(screen.getByRole("radio", { name: "SMS" })).toHaveAttribute("aria-checked", "false");
  });
});
