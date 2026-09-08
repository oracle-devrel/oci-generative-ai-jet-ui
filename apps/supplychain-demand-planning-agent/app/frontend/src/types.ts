/** Wire types between the backend WebSocket and the React UI. */

export type AgentName = "supervisor" | "demand_analyst" | "policy_agent";

export type ServerEvent =
  | { type: "session"; thread_id: string }
  | { type: "pong" }
  | { type: "user_message"; content: string; thread_id: string }
  | { type: "agent_started"; agent: AgentName }
  | { type: "agent_finished"; agent: AgentName; summary?: string }
  | { type: "tool_started"; agent: AgentName | null; tool: string; args: Record<string, unknown> }
  | { type: "tool_finished"; agent: AgentName | null; tool: string; result: string }
  | { type: "token"; agent: AgentName; token: string }
  | { type: "final_answer"; content: string }
  | { type: "stream_end"; content: string }
  | { type: "error"; message: string };

export type ClientEvent =
  | { type: "user_message"; content: string; thread_id?: string }
  | { type: "ping" };

export interface ChatTurn {
  id: string;
  role: "user" | "assistant";
  content: string;
  pending?: boolean;
}

export interface AgentTrace {
  agent: AgentName;
  started?: number;
  finished?: number;
  tokens: string;
  toolCalls: ToolCall[];
  summary?: string;
}

export interface ToolCall {
  id: string;
  tool: string;
  args: Record<string, unknown>;
  result?: string;
  startedAt: number;
  finishedAt?: number;
}

export interface ArchitectureNode {
  id: string;
  label: string;
  kind: "user" | "supervisor" | "specialist" | "store";
}

export interface ArchitectureEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
  dashed?: boolean;
}

export interface ArchitectureGraph {
  nodes: ArchitectureNode[];
  edges: ArchitectureEdge[];
}

export interface TableInfo {
  id: string;
  label: string;
  purpose: string;
  kind: "vector" | "store" | "cache" | "chat" | "checkpoint";
  exists: boolean;
  row_count: number | null;
}

export interface TableColumn {
  name: string;
  type: string;
  length: number | null;
  nullable: boolean;
}

export interface TableRowsResponse {
  table: string;
  columns: TableColumn[];
  rows: Array<Array<string | number | boolean | null>>;
  row_count_total: number | null;
  row_count_shown: number;
  limit: number;
  search: string | null;
}

export interface HealthInfo {
  status: string;
  llm_provider: string;
  llm_model: string;
  onnx_model: string;
  onnx_dim: number;
}
