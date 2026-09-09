import { memo } from "react";
import { motion } from "framer-motion";
import {
  DatabaseIcon,
  MagnifyingGlassIcon,
  BrainIcon,
  FunctionIcon,
} from "@phosphor-icons/react";
import type {
  EloResult,
  FormResult,
  MomentumResult,
  PoissonResult,
  PredictResult,
  ToolCall,
} from "../lib/types";
import { stagger, riseItem } from "../lib/motion";
import { RawJson } from "./RawJson";
import { ProbabilityBar } from "./viz/ProbabilityBar";
import { EloGauges } from "./viz/EloGauges";
import { FormTiles } from "./viz/FormTiles";
import { MomentumTiles } from "./viz/MomentumTiles";
import { PoissonTiles } from "./viz/PoissonTiles";

const VISUAL = new Set([
  "predict_match",
  "get_elo",
  "get_team_form",
  "get_momentum",
  "get_poisson_xg",
]);

function hasError(result: Record<string, unknown>): result is { error: string } {
  return Boolean(result && typeof result === "object" && "error" in result);
}

function argSummary(args: Record<string, unknown>): string {
  const entries = Object.entries(args);
  if (!entries.length) return "";
  return entries
    .map(([k, v]) => `${k}=${typeof v === "string" ? v : JSON.stringify(v)}`)
    .join("  ");
}

/** Small SQL result table for sql_query — render rows rather than raw JSON. */
function SqlTable({ rows }: { rows: Record<string, unknown>[] }) {
  if (!rows.length) return <p className="text-[12px] text-fg-dim">No rows.</p>;
  const cols = Object.keys(rows[0]);
  const shown = rows.slice(0, 8);
  return (
    <div className="overflow-x-auto rounded-lg border border-line-soft">
      <table className="w-full border-collapse font-mono text-[11px]">
        <thead>
          <tr className="bg-surface-2">
            {cols.map((c) => (
              <th
                key={c}
                className="border-b border-line-soft px-2.5 py-1.5 text-left font-medium uppercase tracking-wide text-fg-faint"
              >
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {shown.map((r, i) => (
            <tr key={i} className="odd:bg-surface/40">
              {cols.map((c) => (
                <td key={c} className="border-b border-line-soft px-2.5 py-1.5 tabular-nums text-fg-dim">
                  {r[c] === null ? "—" : String(r[c])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length > shown.length && (
        <p className="px-2.5 py-1.5 font-mono text-[10.5px] text-fg-faint">
          +{rows.length - shown.length} more rows
        </p>
      )}
    </div>
  );
}

function ToolIcon({ name }: { name: string }) {
  const props = { size: 14, weight: "bold" as const, className: "flex-none text-accent" };
  if (name === "sql_query") return <DatabaseIcon {...props} />;
  if (name === "vector_search") return <MagnifyingGlassIcon {...props} />;
  if (name === "remember" || name === "recall") return <BrainIcon {...props} />;
  return <FunctionIcon {...props} />;
}

function renderVisual(call: ToolCall) {
  const r = call.result;
  switch (call.name) {
    case "predict_match":
      return <ProbabilityBar data={r as unknown as PredictResult} variant="inline" />;
    case "get_elo":
      return <EloGauges data={r as unknown as EloResult} />;
    case "get_team_form":
      return <FormTiles data={r as unknown as FormResult} />;
    case "get_momentum":
      return <MomentumTiles data={r as unknown as MomentumResult} />;
    case "get_poisson_xg":
      return <PoissonTiles data={r as unknown as PoissonResult} />;
    default:
      return null;
  }
}

/** A single tool card: header (name + args), then visual body or clean labeled
 *  fallback, plus a collapsible raw-JSON view (default collapsed). */
function ToolCard({ call }: { call: ToolCall }) {
  const err = hasError(call.result);
  const isVisual = VISUAL.has(call.name) && !err;
  const isSql = call.name === "sql_query" && !err && Array.isArray((call.result as { rows?: unknown }).rows);

  return (
    <motion.div
      variants={riseItem}
      className="rounded-[14px] border border-line-soft bg-surface p-4 shadow-[var(--shadow-tint-sm)]"
    >
      <div className="flex items-center gap-2">
        <ToolIcon name={call.name} />
        <span className="font-mono text-[12px] font-medium text-fg">{call.name}</span>
        {argSummary(call.args) && (
          <span className="ml-1 min-w-0 flex-1 truncate font-mono text-[10.5px] text-fg-faint">
            {argSummary(call.args)}
          </span>
        )}
      </div>

      <div className="mt-3">
        {err ? (
          <p className="rounded-lg border border-rose/40 bg-rose/10 px-3 py-2 font-mono text-[11.5px] text-rose">
            {String((call.result as { error: string }).error)}
          </p>
        ) : isVisual ? (
          renderVisual(call)
        ) : isSql ? (
          <SqlTable rows={(call.result as { rows: Record<string, unknown>[] }).rows} />
        ) : (
          <p className="font-mono text-[11.5px] text-fg-dim">
            {summariseGeneric(call)}
          </p>
        )}
      </div>

      <RawJson data={call.result} />
    </motion.div>
  );
}

// One-line human summary for non-visual tools (vector_search, h2h, tournament,
// lookup, remember, recall) before the user expands raw JSON.
function summariseGeneric(call: ToolCall): string {
  const r = call.result as Record<string, unknown>;
  if (call.name === "vector_search" && Array.isArray(r.facts)) {
    return `${(r.facts as unknown[]).length} matching fact(s) retrieved.`;
  }
  if (call.name === "recall" && Array.isArray(r.turns)) {
    return `${(r.turns as unknown[]).length} prior turn(s) recalled.`;
  }
  if (call.name === "remember") {
    return "Fact written to semantic memory.";
  }
  if (call.name === "get_h2h") {
    return `Head-to-head: ${String(r.team_a)} vs ${String(r.team_b)}.`;
  }
  if (call.name === "get_tournament_context") {
    return `Tournament-stage context for ${String(r.team)}.`;
  }
  if (call.name === "lookup_prediction") {
    return "Precomputed prediction.";
  }
  if (call.name === "hybrid_retrieve" && Array.isArray(r.documents)) {
    return `${(r.documents as unknown[]).length} document(s) retrieved via hybrid search.`;
  }
  if (call.name === "build_match_briefing") {
    const bullets = r.narrative_bullets;
    if (Array.isArray(bullets) && bullets.length > 0) {
      return String(bullets[0]);
    }
    return "Match briefing assembled.";
  }
  return "Result available — expand raw JSON.";
}

interface Props {
  trace: ToolCall[];
}

/** Renders a conversation turn's full tool trace as a staggered stack. */
function ToolTraceBase({ trace }: Props) {
  if (!trace?.length) return null;
  return (
    <motion.div
      className="mt-3 grid gap-2.5"
      variants={stagger}
      initial="hidden"
      animate="show"
    >
      <div className="font-mono text-[10.5px] uppercase tracking-[0.12em] text-fg-faint">
        {trace.length} tool {trace.length > 1 ? "calls" : "call"}
      </div>
      {trace.map((call, i) => (
        <ToolCard key={`${call.name}-${i}`} call={call} />
      ))}
    </motion.div>
  );
}

export const ToolTrace = memo(ToolTraceBase);
