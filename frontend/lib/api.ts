import type { Analysis, Blotter, Overview } from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8002";
export const DESK_TOKEN = process.env.NEXT_PUBLIC_DESK_TOKEN ?? "";

function withToken(url: string): string {
  if (!DESK_TOKEN) return url;
  const sep = url.includes("?") ? "&" : "?";
  return `${url}${sep}token=${encodeURIComponent(DESK_TOKEN)}`;
}

export const WS_URL = withToken(process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8002/ws");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(DESK_TOKEN ? { "X-Desk-Token": DESK_TOKEN } : {}),
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  overview: () => request<Overview>("/api/overview"),
  instruments: (sleeve?: string) =>
    request<{ instruments: Overview["instruments"] }>(
      sleeve ? `/api/instruments?sleeve=${sleeve}` : "/api/instruments",
    ),
  blotter: () => request<Blotter>("/api/blotter"),
  analysis: () => request<Analysis>("/api/analysis"),
  equity: (window: "today" | "7d" | "30d" | "all") =>
    request<{ window: string; points: Overview["equity"] }>(`/api/equity?window=${window}`),
  settings: () => request<Record<string, string>>("/api/settings"),
  control: (action: string) => request<{ ok: boolean }>(`/api/control/${action}`, { method: "POST" }),
  patchSettings: (body: Record<string, string | number>) =>
    request<Record<string, string>>("/api/settings", {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
};
