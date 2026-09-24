import { afterEach, describe, expect, it, vi } from "vitest";

import { analyzeStream, ApiError } from "@/lib/api";
import type { StreamEvent } from "@/types/api";

function ndjsonResponse(chunks: string[], status = 200) {
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      const enc = new TextEncoder();
      chunks.forEach((c) => controller.enqueue(enc.encode(c)));
      controller.close();
    },
  });
  return new Response(stream, { status, headers: { "Content-Type": "application/x-ndjson" } });
}

const RESULT = { id: "abc", risk_score: 88, risk_level: "CRITICAL" };

afterEach(() => vi.restoreAllMocks());

describe("analyzeStream", () => {
  it("parses events split across network chunks and resolves with the result", async () => {
    const lines = [
      JSON.stringify({ type: "stage", stage: "validate" }),
      JSON.stringify({ type: "step", step: { tool: "text_classifier", stage: "analyze", status: "done", duration_ms: 3, label: "x" } }),
      JSON.stringify({ type: "result", result: RESULT }),
    ].join("\n") + "\n";
    // Split mid-line to prove buffering works.
    vi.spyOn(globalThis, "fetch").mockResolvedValue(ndjsonResponse([lines.slice(0, 30), lines.slice(30, 95), lines.slice(95)]));
    const seen: StreamEvent["type"][] = [];
    const result = await analyzeStream({ kind: "text", text: "hello there", channel: "sms" }, (e) => seen.push(e.type));
    expect(result).toMatchObject(RESULT);
    expect(seen).toEqual(["stage", "step", "result"]);
  });

  it("sends the anonymous device header and the stream flag", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      ndjsonResponse([JSON.stringify({ type: "result", result: RESULT }) + "\n"]));
    await analyzeStream({ kind: "url", url: "http://x.xyz" }, () => {});
    const [url, init] = spy.mock.calls[0];
    expect(String(url)).toContain("/api/analyze/url?stream=true");
    expect((init?.headers as Record<string, string>)["X-Sentinel-Client"]).toMatch(/^[A-Za-z0-9-]{8,64}$/);
  });

  it("turns an in-stream error event into an ApiError with the friendly message", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(ndjsonResponse([
      JSON.stringify({ type: "stage", stage: "extract" }) + "\n",
      JSON.stringify({ type: "error", status: 422, error: { code: "QR_NOT_FOUND", message: "We couldn't detect a QR code in this image." } }) + "\n",
    ]));
    const err = await analyzeStream({ kind: "qr", file: new File(["x"], "q.png", { type: "image/png" }) }, () => {}).catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.code).toBe("QR_NOT_FOUND");
    expect(err.message).toMatch(/couldn't detect a QR code/);
  });

  it("maps HTTP validation errors before the stream starts", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(
      JSON.stringify({ error: { code: "FILE_TOO_LARGE", message: "That file is larger than the 8 MB limit." } }), { status: 413 }));
    const err = await analyzeStream({ kind: "image", file: new File(["x"], "a.png", { type: "image/png" }) }, () => {}).catch((e) => e);
    expect(err.status).toBe(413);
    expect(err.code).toBe("FILE_TOO_LARGE");
  });

  it("reports a network failure without leaking technical details", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));
    const err = await analyzeStream({ kind: "text", text: "hello there", channel: "sms" }, () => {}).catch((e) => e);
    expect(err.code).toBe("NETWORK");
    expect(err.message).not.toMatch(/TypeError|fetch/);
  });
});
