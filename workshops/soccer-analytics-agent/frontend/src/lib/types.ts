// Wire types — mirror the FastAPI contract exactly. Do not extend the
// request/response shapes; the backend is fixed.

export interface ToolCall {
  name: ToolName;
  args: Record<string, unknown>;
  result: Record<string, unknown>;
}

export type ToolName =
  | "sql_query"
  | "vector_search"
  | "hybrid_retrieve"
  | "predict_match"
  | "build_match_briefing"
  | "get_elo"
  | "get_team_form"
  | "get_h2h"
  | "get_momentum"
  | "get_poisson_xg"
  | "get_tournament_context"
  | "lookup_prediction"
  | "remember"
  | "recall";

export interface ChatResponse {
  session_id: string;
  reply: string;
  tool_trace: ToolCall[];
}

export interface ApiError {
  session_id?: string;
  error: string;
  error_type?: string;
  detail?: string;
}

export interface Health {
  oracle: boolean;
  grok_configured: boolean;
}

// Result shapes for the tools we render visually (confirmed against
// feature_runtime.py / inference/live.py).
export interface PredictResult {
  home_team: string;
  away_team: string;
  prob_home_win: number;
  prob_draw: number;
  prob_away_win: number;
  model_version: string;
  source: string;
  features_used: number;
}

export interface EloResult {
  team: string;
  elo: number;
  world_cup_elo: number;
  continental_elo: number;
  qualifier_elo: number;
  friendly_elo: number;
  vs_average: number;
}

export interface FormResult {
  team: string;
  n: number;
  form: number;
  weighted_form: number;
  avg_goals_scored: number;
  avg_goals_conceded: number;
  goal_diff_avg: number;
  total_matches: number;
}

export interface MomentumResult {
  team: string;
  n: number;
  current_streak: number;
  unbeaten_streak: number;
  clean_sheet_pct: number;
  comeback_rate: number;
  draw_tendency: number;
  blowout_win_pct: number;
  blowout_loss_pct: number;
  shutout_loss_pct: number;
}

export interface PoissonResult {
  home_team: string;
  away_team: string;
  home_lambda: number;
  away_lambda: number;
  home_poisson_win: number;
  home_poisson_draw: number;
  home_scoring_variance: number;
  away_scoring_variance: number;
  home_overperformance: number;
  away_overperformance: number;
}

// Conversation model.
export type Role = "user" | "assistant";

export interface Message {
  id: string;
  role: Role;
  text: string;
  trace?: ToolCall[];
  isError?: boolean;
}

export type HealthStatus = "connecting" | "live" | "db-only" | "offline";
