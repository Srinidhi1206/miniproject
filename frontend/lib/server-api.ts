import "server-only";

import type { GuideDetail, GuideSummary } from "@/types/api";

// Server components may reach the backend on an internal address (e.g. docker network).
const BASE = (process.env.INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

async function get<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${BASE}${path}`, { next: { revalidate: 300 } });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

export const serverApi = {
  guides: () => get<GuideSummary[]>("/api/safety-guides"),
  guide: (slug: string) => get<GuideDetail>(`/api/safety-guides/${encodeURIComponent(slug)}`),
};
