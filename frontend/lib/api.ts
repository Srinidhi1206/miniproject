import { getClientId } from "@/lib/client-id";
import type {
  AnalysisResult, ApiErrorBody, Channel, ClientStats, GuideDetail, GuideSummary, Health, HistoryPage,
  ReportOptions, ReportReceipt, ScamMapData, StreamEvent,
} from "@/types/api";

// Inlined at build time. The localhost fallback is for local development only;
// Vercel builds refuse to proceed without a real URL — see next.config.ts.
export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {
  code: string;
  hint?: string;
  status: number;
  constructor(status: number, body: ApiErrorBody) {
    super(body.message);
    this.status = status;
    this.code = body.code;
    this.hint = body.hint;
  }
}

const NETWORK_ERROR: ApiErrorBody = {
  code: "NETWORK",
  message: "SENTINEL's analysis service can't be reached right now.",
  hint: "Check your connection and try again. If the service was idle, it can take up to a minute to wake up.",
};

async function toApiError(res: Response): Promise<ApiError> {
  try {
    const body = await res.json();
    if (body?.error?.message) return new ApiError(res.status, body.error);
  } catch {
    /* fall through */
  }
  return new ApiError(res.status, { code: `HTTP_${res.status}`, message: "The request could not be completed." });
}

function headers(extra?: HeadersInit): HeadersInit {
  return { "X-Sentinel-Client": getClientId(), ...extra };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...init, headers: headers(init?.headers) });
  } catch {
    throw new ApiError(0, NETWORK_ERROR);
  }
  if (!res.ok) throw await toApiError(res);
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

/* ------------------------------------------------------------------ analyze */

export type AnalyzeInput =
  | { kind: "text"; text: string; channel: Channel }
  | { kind: "url"; url: string }
  | { kind: "image"; file: File; channel?: Channel }
  | { kind: "qr"; file: File };

/**
 * Runs an analysis with live progress. The backend streams NDJSON events as each
 * agent tool finishes; `onEvent` receives them in order. Resolves with the final result.
 */
export async function analyzeStream(
  input: AnalyzeInput,
  onEvent: (e: StreamEvent) => void,
  signal?: AbortSignal,
): Promise<AnalysisResult> {
  let body: BodyInit;
  let extra: HeadersInit = {};
  if (input.kind === "text") {
    body = JSON.stringify({ text: input.text, channel: input.channel });
    extra = { "Content-Type": "application/json" };
  } else if (input.kind === "url") {
    body = JSON.stringify({ url: input.url });
    extra = { "Content-Type": "application/json" };
  } else {
    const fd = new FormData();
    fd.append("file", input.file);
    if (input.kind === "image" && input.channel) fd.append("channel", input.channel);
    body = fd;
  }

  let res: Response;
  try {
    res = await fetch(`${API_URL}/api/analyze/${input.kind}?stream=true`, {
      method: "POST", body, headers: headers(extra), signal,
    });
  } catch (e) {
    if ((e as Error).name === "AbortError") throw e;
    throw new ApiError(0, NETWORK_ERROR);
  }
  if (!res.ok || !res.body) throw await toApiError(res);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result: AnalysisResult | null = null;
  for (;;) {
    const { value, done } = await reader.read();
    if (value) buffer += decoder.decode(value, { stream: true });
    let nl: number;
    while ((nl = buffer.indexOf("\n")) >= 0) {
      const line = buffer.slice(0, nl).trim();
      buffer = buffer.slice(nl + 1);
      if (!line) continue;
      const event = JSON.parse(line) as StreamEvent;
      if (event.type === "error") throw new ApiError(event.status, event.error);
      if (event.type === "result") result = event.result;
      onEvent(event);
    }
    if (done) break;
  }
  if (!result) throw new ApiError(500, { code: "INCOMPLETE", message: "The analysis ended unexpectedly. Please try again." });
  return result;
}

/* ---------------------------------------------------------------- read APIs */

export const api = {
  analysis: (id: string) => request<AnalysisResult>(`/api/analysis/${encodeURIComponent(id)}`),
  history: (params: Record<string, string | number | undefined>) => {
    const q = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => v !== undefined && v !== "" && q.set(k, String(v)));
    return request<HistoryPage>(`/api/history?${q}`);
  },
  clearHistory: () => request<void>("/api/history", { method: "DELETE" }),
  stats: () => request<ClientStats>("/api/stats"),
  reportOptions: () => request<ReportOptions>("/api/reports/options"),
  submitReport: (fd: FormData) => request<ReportReceipt>("/api/reports", { method: "POST", body: fd }),
  scamMap: (params: { type?: string; region?: string; days?: number; include_demo?: boolean }) => {
    const q = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => v !== undefined && v !== "" && q.set(k, String(v)));
    return request<ScamMapData>(`/api/scam-map?${q}`);
  },
  guides: () => request<GuideSummary[]>("/api/safety-guides"),
  guide: (slug: string) => request<GuideDetail>(`/api/safety-guides/${encodeURIComponent(slug)}`),
  health: () => request<Health>("/api/health"),
};
