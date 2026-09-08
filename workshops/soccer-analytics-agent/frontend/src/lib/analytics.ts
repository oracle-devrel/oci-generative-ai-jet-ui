// Distill the conversation's tool_trace into the structured analytics the
// persistent side panel renders for the most recent match / team.

import type {
  EloResult,
  FormResult,
  Message,
  MomentumResult,
  PoissonResult,
  PredictResult,
  ToolCall,
} from "./types";

export interface AnalyticsSnapshot {
  prediction?: PredictResult;
  elo: EloResult[]; // most-recent first, deduped by team
  form: FormResult[];
  momentum?: MomentumResult;
  poisson?: PoissonResult;
  subjectTeams: string[]; // teams in focus, for the panel header
}

function isResult(call: ToolCall, name: string): boolean {
  return call.name === name && call.result && !("error" in call.result);
}

// Flatten every tool call across the conversation in chronological order.
function allCalls(messages: Message[]): ToolCall[] {
  const calls: ToolCall[] = [];
  for (const m of messages) {
    if (m.trace) calls.push(...m.trace);
  }
  return calls;
}

function lastOf<T>(calls: ToolCall[], name: string): T | undefined {
  for (let i = calls.length - 1; i >= 0; i--) {
    if (isResult(calls[i], name)) return calls[i].result as unknown as T;
  }
  return undefined;
}

// Collect the most-recent N distinct-team results for a tool (e.g. elo for
// both teams in the latest comparison), newest first.
function recentByTeam<T extends { team: string }>(
  calls: ToolCall[],
  name: string,
  max = 2,
): T[] {
  const out: T[] = [];
  const seen = new Set<string>();
  for (let i = calls.length - 1; i >= 0 && out.length < max; i--) {
    if (!isResult(calls[i], name)) continue;
    const r = calls[i].result as unknown as T;
    if (seen.has(r.team)) continue;
    seen.add(r.team);
    out.push(r);
  }
  return out;
}

export function buildSnapshot(messages: Message[]): AnalyticsSnapshot {
  const calls = allCalls(messages);

  const prediction = lastOf<PredictResult>(calls, "predict_match");
  const poisson = lastOf<PoissonResult>(calls, "get_poisson_xg");
  const momentum = lastOf<MomentumResult>(calls, "get_momentum");
  const elo = recentByTeam<EloResult>(calls, "get_elo", 2);
  const form = recentByTeam<FormResult>(calls, "get_team_form", 2);

  // Derive the teams in focus: prefer the prediction matchup, else elo/form.
  const subjectTeams: string[] = [];
  const push = (t?: string) => {
    if (t && !subjectTeams.includes(t)) subjectTeams.push(t);
  };
  if (prediction) {
    push(prediction.home_team);
    push(prediction.away_team);
  }
  if (poisson) {
    push(poisson.home_team);
    push(poisson.away_team);
  }
  elo.forEach((e) => push(e.team));
  form.forEach((f) => push(f.team));

  return { prediction, elo, form, momentum, poisson, subjectTeams };
}

export function hasAnalytics(s: AnalyticsSnapshot): boolean {
  return Boolean(
    s.prediction ||
      s.poisson ||
      s.momentum ||
      s.elo.length ||
      s.form.length,
  );
}
