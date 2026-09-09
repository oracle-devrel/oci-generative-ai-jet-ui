// Typed client for the soccer agent API. Same-origin in production (served
// by FastAPI at /), dev-proxied to 127.0.0.1:8000 by vite.config.ts.

import type { ApiError, ChatResponse, Health } from "./types";

export class AgentApiError extends Error {
  detail?: string;
  errorType?: string;
  constructor(message: string, opts?: { detail?: string; errorType?: string }) {
    super(message);
    this.name = "AgentApiError";
    this.detail = opts?.detail;
    this.errorType = opts?.errorType;
  }
}

async function readJson<T>(resp: Response): Promise<T> {
  const ct = resp.headers.get("content-type") ?? "";
  if (ct.includes("application/json")) {
    return (await resp.json()) as T;
  }
  // Non-JSON error body (e.g. proxy/HTML failure page).
  const text = await resp.text();
  throw new AgentApiError(`HTTP ${resp.status}`, { detail: text.slice(0, 500) });
}

export async function getHealth(): Promise<Health> {
  const resp = await fetch("/health");
  if (!resp.ok) throw new AgentApiError(`HTTP ${resp.status}`);
  return readJson<Health>(resp);
}

export async function sendChat(
  message: string,
  sessionId: string | null,
  signal?: AbortSignal,
): Promise<ChatResponse> {
  const resp = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message }),
    signal,
  });

  const data = await readJson<ChatResponse | ApiError>(resp);

  if (!resp.ok || "error" in data) {
    const err = data as ApiError;
    throw new AgentApiError(err.error ?? `HTTP ${resp.status}`, {
      detail: err.detail,
      errorType: err.error_type,
    });
  }
  return data as ChatResponse;
}

export async function clearMemory(sessionId: string): Promise<void> {
  try {
    await fetch(`/memory/${encodeURIComponent(sessionId)}`, { method: "DELETE" });
  } catch {
    // Reset is best-effort; the client clears local state regardless.
  }
}
