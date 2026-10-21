import type {
  AppStatus,
  AskRequest,
  AskResponse,
  CorpusResponse,
  OracleInspectionResponse,
  ResetResponse,
  SeedResponse,
} from "@oracle-langchain-js-rag/shared";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  const payload = (await response.json().catch(() => ({}))) as T & { error?: string };
  if (!response.ok) {
    throw new Error(payload.error || `Request failed with ${response.status}`);
  }
  return payload;
}

export function getStatus(): Promise<AppStatus> {
  return request<AppStatus>("/api/status");
}

export function getCorpus(): Promise<CorpusResponse> {
  return request<CorpusResponse>("/api/corpus");
}

export function getOracleInspection(): Promise<OracleInspectionResponse> {
  return request<OracleInspectionResponse>("/api/inspect");
}

export function seedCorpus(): Promise<SeedResponse> {
  return request<SeedResponse>("/api/seed", { method: "POST" });
}

export function resetCorpus(): Promise<ResetResponse> {
  return request<ResetResponse>("/api/reset", { method: "POST" });
}

export function askQuestion(body: AskRequest): Promise<AskResponse> {
  return request<AskResponse>("/api/ask", {
    method: "POST",
    body: JSON.stringify(body),
  });
}
