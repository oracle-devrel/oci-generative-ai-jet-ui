import { useEffect, useMemo, useState } from "react";
import {
  Bot, Play, Eraser, Coins, Cpu, Clock, Zap, LoaderCircle, CircleCheck,
  Brain, Wrench, Sparkles, Moon,
} from "lucide-react";
import { DEFAULT_RECALL_SECONDS } from "../hooks/useAmlLoop";

// Shown before the first aml_status lands (and when the capture predates it) so
// the instrument still names the run it is replaying.
const MODEL_FALLBACK = "xai.grok-4.3";
const CAPTURED_DATE_FALLBACK = "2026-09-29";
const CAPTURED_SECONDS_FALLBACK = 89;

const STEP_META = {
  context: { icon: Brain,    color: "text-accent-memory", bar: "bg-accent-memory" },
  tool:    { icon: Wrench,   color: "text-accent-skill",  bar: "bg-accent-skill" },
  model:   { icon: Sparkles, color: "text-accent-oracle", bar: "bg-accent-oracle" },
};

const DECISION_META = {
  ESCALATE:        { color: "text-accent-sql",      bar: "bg-accent-sql" },
  KYC_REVIEW:      { color: "text-accent-tool",     bar: "bg-accent-tool" },
  DISMISS:         { color: "text-text-secondary",  bar: "bg-text-secondary" },
  REVIEW_REQUIRED: { color: "text-accent-oracle",   bar: "bg-accent-oracle" },
};

// `risk_rating` is a 1–100 score in FINANCE; named bands are tolerated in case
// a capture predates that. Banded like the token meter's bar.
const RISK_META = {
  HIGH: "bg-accent-sql/20 text-accent-sql",
  MEDIUM: "bg-accent-tool/20 text-accent-tool",
  LOW: "bg-text-secondary/15 text-text-secondary",
};

function riskChip(rating) {
  if (rating == null || rating === "") return null;
  const score = Number(rating);
  if (Number.isFinite(score)) {
    return {
      label: `risk ${score}`,
      cls: score >= 70 ? RISK_META.HIGH : score >= 40 ? RISK_META.MEDIUM : RISK_META.LOW,
    };
  }
  return { label: String(rating), cls: RISK_META[rating] || RISK_META.LOW };
}

function fmtDate(iso) {
  if (!iso) return null;
  const m = String(iso).match(/^\d{4}-\d{2}-\d{2}/);
  return m ? m[0] : String(iso);
}

function fmtClock(iso) {
  if (!iso) return "—";
  const t = new Date(iso).toLocaleTimeString([], {
    hour: "2-digit", minute: "2-digit", second: "2-digit",
  });
  return t;
}

function fmtMs(ms) {
  if (ms == null) return "—";
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${Math.round(ms)}ms`;
}

function fmtSeconds(s) {
  if (s == null) return "—";
  return `${Number(s).toFixed(1)}s`;
}

function fmtExposure(cents) {
  if (cents == null) return "—";
  return `$${(cents / 100).toLocaleString()}`;
}

function Stat({ label, value, color = "text-text-accent" }) {
  return (
    <div className="flex flex-col">
      <span className="text-[9px] uppercase tracking-wider text-text-muted">{label}</span>
      <span className={color}>{value}</span>
    </div>
  );
}

/**
 * One replayed step. While it runs, a bar fills over the step's *captured*
 * duration (the model was replaying a recording — the timing is known up
 * front), then the row collapses to the measured duration and token count.
 */
function StepRow({ step }) {
  const running = step.status === "running";
  const [armed, setArmed] = useState(false);

  useEffect(() => {
    if (!running) {
      setArmed(false);
      return;
    }
    const id = window.requestAnimationFrame(() => setArmed(true));
    return () => window.cancelAnimationFrame(id);
  }, [running]);

  const meta = STEP_META[step.kind] || STEP_META.tool;
  const Icon = meta.icon;
  const resultLines = Array.isArray(step.result_lines)
    ? step.result_lines.join("\n")
    : step.result_lines;

  return (
    <div className="px-3 py-1.5">
      <div className="flex items-center gap-2">
        <Icon size={11} className={`${meta.color} shrink-0`} />
        <span className="text-[10px] font-mono text-text-muted shrink-0">{step.step}</span>
        <span className="text-[11px] text-text-accent truncate">{step.label || step.kind}</span>
        <span className="ml-auto shrink-0 text-[10px] font-mono text-text-muted">
          {running
            ? step.planned_ms != null
              ? `${(step.planned_ms / 1000).toFixed(1)}s planned`
              : "…"
            : `${fmtMs(step.duration_ms)}${step.tokens ? ` · ${step.tokens} tok` : ""}`}
        </span>
      </div>

      {running && (
        <div className="mt-1 h-1 bg-white/[0.05] rounded overflow-hidden">
          <div
            className={`h-full transition-all ease-linear ${meta.bar}`}
            style={{
              width: armed ? "100%" : "0%",
              transitionDuration: `${Math.max(150, step.planned_ms || 0)}ms`,
            }}
          />
        </div>
      )}

      {step.kind === "tool" && step.tool && (
        <div className="mt-1 rounded border border-white/5 bg-black/30 px-2 py-1">
          <div className={`text-[10px] font-mono ${meta.color}`}>{step.tool}</div>
          <pre className="text-[10px] font-mono text-text-muted whitespace-pre-wrap break-all">
            {JSON.stringify(step.args ?? {}, null, 1)}
          </pre>
        </div>
      )}

      {/* Context steps carry the whole evidence pack the model was shown. */}
      {step.kind === "context" && Array.isArray(step.detail) && step.detail.length > 0 && (
        <pre className="mt-1 max-h-32 overflow-y-auto rounded border border-white/5 bg-black/30 px-2 py-1 text-[10px] font-mono text-text-muted whitespace-pre-wrap">
          {step.detail.join("\n")}
        </pre>
      )}

      {step.status === "done" && resultLines && (
        <pre className="mt-1 max-h-24 overflow-y-auto text-[10px] font-mono text-text-secondary/70 whitespace-pre-wrap">
          {resultLines}
        </pre>
      )}
    </div>
  );
}

function DecisionCard({ alert }) {
  const dec = alert.decision || {};
  const meta = DECISION_META[dec.decision] || DECISION_META.DISMISS;
  // Confidence arrives as a 0–1 score; tolerate a 0–100 capture too.
  const raw = dec.confidence ?? 0;
  const pct = Math.max(0, Math.min(100, Math.round(raw <= 1 ? raw * 100 : raw)));

  return (
    <div className="border-t border-white/5 bg-white/[0.015] px-3 py-2 space-y-1.5">
      <div className="flex items-center gap-2 flex-wrap">
        <span className={`text-sm font-semibold tracking-wide ${meta.color}`}>
          {dec.decision || "—"}
        </span>
        <span
          className={`text-[9px] font-mono px-1.5 py-0.5 rounded ${
            alert.mode === "captured"
              ? "bg-accent-memory/15 text-accent-memory"
              : "bg-accent-sql/15 text-accent-sql"
          }`}
        >
          {alert.mode === "captured" ? "captured" : "no capture → human review"}
        </span>
        <span className="ml-auto text-[10px] font-mono text-text-muted">
          {fmtMs(alert.elapsed_ms)}{alert.tokens ? ` · ${alert.tokens} tok` : ""}
        </span>
      </div>

      <div className="flex items-center gap-2">
        <span className="text-[9px] uppercase tracking-wider text-text-muted shrink-0">confidence</span>
        <div className="flex-1 h-1.5 bg-white/[0.05] rounded overflow-hidden">
          <div className={`h-full transition-all duration-500 ${meta.bar}`} style={{ width: `${pct}%` }} />
        </div>
        <span className="text-[10px] font-mono text-text-secondary shrink-0">{pct}%</span>
      </div>

      {dec.rationale && (
        <div className="text-[11px] text-text-accent leading-snug">{dec.rationale}</div>
      )}

      <div className="text-[10px]">
        <span className="uppercase tracking-wider text-text-muted">next</span>{" "}
        <span className="text-text-secondary">{dec.recommended_next_action || "—"}</span>
      </div>

      <div className="flex items-center gap-3 text-[10px] font-mono flex-wrap">
        <span className="text-text-muted">
          sar reason <span className="text-accent-tool">{dec.sar_reason_code || "—"}</span>
        </span>
        {alert.ledger && (
          <span className="text-accent-memory">
            AGENT.AML_REPLAY <span className="text-text-muted">←</span> row written
          </span>
        )}
      </div>

      {alert.mode === "captured" && (
        <div className="text-[9px] font-mono text-text-muted/70 leading-snug">
          recorded decision · the evidence pack above is assembled live, so its txns and
          totals can differ from the ones the recorded rationale cites.
        </div>
      )}
    </div>
  );
}

function AlertCard({ alert, position, total }) {
  const risk = riskChip(alert.alert?.risk_rating);
  return (
    <div className="border border-white/5 rounded bg-bg-elev overflow-hidden">
      <div className="px-3 py-1.5 flex items-center gap-2 border-b border-white/5">
        <span className="text-[9px] font-mono text-text-muted shrink-0">
          {/* Render position, not the server's alert index — the numbering
              convention is the backend's business. */}
          {position + 1}/{total || "?"}
        </span>
        <span className="text-[11px] text-text-primary truncate">
          {alert.alert?.customer_name || alert.alert?.customer_id || "…"}
        </span>
        {alert.alert?.typology && (
          <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-accent-skill/15 text-accent-skill shrink-0">
            {alert.alert.typology}
          </span>
        )}
        {risk && (
          <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded shrink-0 ${risk.cls}`}>
            {risk.label}
          </span>
        )}
        <span className="ml-auto text-[10px] font-mono text-text-muted shrink-0">
          {fmtExposure(alert.alert?.exposure_cents)}
        </span>
        <span
          className={`text-[9px] font-mono px-1.5 py-0.5 rounded shrink-0 ${
            alert.alert?.capture
              ? "bg-accent-memory/15 text-accent-memory"
              : "bg-accent-sql/15 text-accent-sql"
          }`}
        >
          {alert.alert?.capture ? "capture" : "human review"}
        </span>
      </div>

      {alert.steps.length === 0 ? (
        <div className="px-3 py-2 text-[10px] font-mono text-text-muted italic">queued…</div>
      ) : (
        <div className="divide-y divide-white/[0.03]">
          {alert.steps.map((s) => (
            <StepRow key={`${alert.index}-${s.step}`} step={s} />
          ))}
        </div>
      )}

      {alert.decision && <DecisionCard alert={alert} />}
    </div>
  );
}

function QueuePreview({ queue }) {
  if (queue.length === 0) {
    return (
      <div className="text-[10px] text-text-muted italic px-1">
        queue is clear — new FM transactions flagged for triage will appear here
      </div>
    );
  }
  return (
    <div className="border border-white/5 rounded bg-bg-elev overflow-hidden">
      <div className="px-3 py-1.5 border-b border-white/5 flex items-center gap-2">
        <span className="text-[10px] uppercase tracking-wider text-text-muted">queue</span>
        <span className="text-[10px] font-mono text-text-muted">{queue.length} awaiting triage</span>
      </div>
      <table className="w-full text-[10px] font-mono border-collapse">
        <thead>
          <tr className="text-text-muted">
            <th className="text-left px-3 py-1 font-normal border-b border-white/5">customer</th>
            <th className="text-left px-3 py-1 font-normal border-b border-white/5">typology</th>
            <th className="text-right px-3 py-1 font-normal border-b border-white/5">exposure</th>
            <th className="text-right px-3 py-1 font-normal border-b border-white/5">blocked</th>
            <th className="text-right px-3 py-1 font-normal border-b border-white/5">prior SARs</th>
            <th className="text-left px-3 py-1 font-normal border-b border-white/5">path</th>
          </tr>
        </thead>
        <tbody>
          {queue.map((a, i) => (
            <tr key={`${a.customer_id}-${a.window_end}-${i}`} className="border-b border-white/[0.03]">
              <td className="px-3 py-1 text-text-primary truncate">{a.customer_name || a.customer_id}</td>
              <td className="px-3 py-1 text-accent-skill">{a.typology || "—"}</td>
              <td className="px-3 py-1 text-right text-accent-tool">{fmtExposure(a.exposure_cents)}</td>
              <td className="px-3 py-1 text-right text-accent-sql">{a.blocked_txns ?? 0}</td>
              <td className="px-3 py-1 text-right text-text-secondary">{a.prior_sars ?? 0}</td>
              <td className="px-3 py-1">
                <span
                  className={`text-[9px] px-1.5 py-0.5 rounded ${
                    a.capture
                      ? "bg-accent-memory/15 text-accent-memory"
                      : "bg-accent-sql/15 text-accent-sql"
                  }`}
                >
                  {a.capture ? "capture" : "human review"}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RecallBlock({ recall, now, onRecall }) {
  const running = !!recall?.running;
  const startedMs = Date.parse(recall?.started_at || "");
  const elapsed =
    running && Number.isFinite(startedMs) ? Math.max(0, (now - startedMs) / 1000) : 0;
  const budget = recall?.seconds || DEFAULT_RECALL_SECONDS;
  const pct = Math.min(100, Math.round((elapsed / budget) * 100));

  return (
    <div className="border border-white/5 rounded bg-bg-elev px-3 py-2 space-y-2">
      <div className="flex items-center gap-2">
        <Moon size={12} className="text-accent-memory shrink-0" />
        <span className="text-[11px] text-text-primary">Morning recall</span>
        <span className="text-[10px] text-text-muted truncate">
          what the agent knew before the queue was worked
        </span>
        <button
          onClick={onRecall}
          disabled={running}
          title="ask the agent to recap the morning (second captured call)"
          className="ml-auto shrink-0 flex items-center gap-1 text-[10px] px-2 py-0.5 rounded border border-white/5 text-text-secondary hover:text-text-primary hover:border-accent-memory/40 disabled:opacity-40"
        >
          {running ? (
            <LoaderCircle size={10} className="animate-spin text-accent-memory" />
          ) : (
            <Sparkles size={10} className="text-accent-memory" />
          )}
          recall the morning
        </button>
      </div>

      {running && (
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-[10px] font-mono text-text-muted">
            <LoaderCircle size={10} className="animate-spin text-accent-memory" />
            <span>thinking…</span>
            <span className="ml-auto">
              {elapsed.toFixed(1)}s / {budget.toFixed(1)}s
            </span>
          </div>
          <div className="h-1 bg-white/[0.05] rounded overflow-hidden">
            <div
              className="h-full bg-accent-memory transition-all ease-linear"
              style={{ width: `${pct}%`, transitionDuration: "250ms" }}
            />
          </div>
        </div>
      )}

      {!running && recall?.answer_lines?.length > 0 && (
        <>
          <pre className="max-h-56 overflow-y-auto rounded border border-white/5 bg-black/30 px-2 py-1 text-[10px] font-mono text-text-accent whitespace-pre-wrap">
            {recall.answer_lines.join("\n")}
          </pre>
          <div className="text-[9px] font-mono text-text-muted">
            recap took {fmtSeconds(recall.seconds)} · {recall.tokens || 0} tok
          </div>
        </>
      )}
    </div>
  );
}

/**
 * The Autonomous tab — a live visualizer for the autonomous AML triage loop.
 *
 * It is a *replay*: the alerts below were triaged by a captured grok run, and
 * the panel streams the recorded context packs, tool calls and decisions back
 * at wall-clock speed, then writes the result to AGENT.AML_REPLAY. Because the
 * run is a recording, working the queue costs no live model tokens.
 */
export default function AutonomousLoop({ aml, identity }) {
  const [now, setNow] = useState(() => Date.now());
  const running = aml.state === "running";
  const recallRunning = !!aml.recall?.running;

  // Wall-clock readouts (sweep cost meter, recall thinking bar) only need a
  // tick while something is actually in flight.
  useEffect(() => {
    if (!running && !recallRunning) return;
    const id = window.setInterval(() => setNow(Date.now()), 250);
    return () => window.clearInterval(id);
  }, [running, recallRunning]);

  const alerts = useMemo(
    () => [...(aml.run?.alerts || [])].sort((a, b) => a.index - b.index),
    [aml.run],
  );
  // Newest first — the freshest FM hits are the ones that still need a human.
  const queue = useMemo(
    () =>
      [...(aml.queue || [])].sort((a, b) =>
        String(b.window_end || "").localeCompare(String(a.window_end || "")),
      ),
    [aml.queue],
  );

  const model = aml.status?.model || aml.run?.model || MODEL_FALLBACK;
  const capturedAt =
    fmtDate(aml.status?.captured_at || aml.run?.captured_at) || CAPTURED_DATE_FALLBACK;

  const totals = aml.last?.totals || null;
  const liveSteps = alerts.reduce(
    (n, a) => n + a.steps.filter((s) => s.kind === "model" && s.status === "done").length,
    0,
  );
  const liveTokens = alerts.reduce((n, a) => n + (a.tokens || 0), 0);
  const liveAlerts = alerts.filter((a) => a.decision).length;

  // Wall clock of the replay itself — the chip contrasts it with the minutes
  // the original run took, which is the whole point of the capture.
  const startedMs = Date.parse(aml.run?.started_at || "");
  const wall = running
    ? Number.isFinite(startedMs)
      ? (now - startedMs) / 1000
      : null
    : totals?.seconds ?? null;
  const capturedSeconds = totals?.captured_seconds ?? CAPTURED_SECONDS_FALLBACK;

  const canClear = !running && !!aml.last;

  return (
    <div className="h-full flex flex-col min-h-0">
      {/* Header strip — capture badge, run controls, cost meter */}
      <div className="shrink-0 border-b border-white/5 bg-bg-panel/60 px-3 py-2 space-y-1.5">
        <div className="flex items-center gap-2 flex-wrap">
          <Bot size={12} className="text-accent-oracle shrink-0" />
          <span className="text-[10px] uppercase tracking-wider text-text-muted">Autonomous</span>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-accent-oracle/15 text-accent-oracle">
            {model} · captured {capturedAt}
          </span>
          <span
            className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-white/5 text-text-secondary"
            title="the replay acts as this DB principal when writing the ledger"
          >
            as {identity?.id || "agent"}
          </span>

          <span className="ml-auto flex items-center gap-2 shrink-0">
            <button
              onClick={() => aml.runSweep(3)}
              disabled={running}
              title="replay the captured triage run over the queued alerts"
              className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded border border-accent-oracle/40 bg-accent-oracle/10 text-accent-oracle hover:bg-accent-oracle/20 disabled:opacity-50 disabled:hover:bg-accent-oracle/10"
            >
              {running ? <LoaderCircle size={11} className="animate-spin" /> : <Play size={11} />}
              {running ? "running…" : "Work the queue"}
            </button>
            {canClear && (
              <button
                onClick={aml.clear}
                title="clear the replayed ledger (queue untouched)"
                className="flex items-center gap-1 text-[10px] text-text-muted hover:text-text-primary"
              >
                <Eraser size={10} />
                clear
              </button>
            )}
          </span>
        </div>

        <div className="flex items-center gap-3 text-[10px] font-mono text-text-muted flex-wrap">
          <span className="flex items-center gap-1">
            <Coins size={10} className="text-accent-tool" />
            {running ? `${liveAlerts}/${aml.run?.alertsTotal || "?"}` : totals?.alerts ?? "—"} alerts
          </span>
          <span className="flex items-center gap-1">
            <Cpu size={10} className="text-accent-skill" />
            {running ? liveSteps : totals?.model_calls ?? "—"} model calls
          </span>
          <span className="flex items-center gap-1">
            <Zap size={10} className="text-accent-memory" />
            {(running ? liveTokens : totals?.tokens ?? 0).toLocaleString()} tokens
          </span>
          <span className="flex items-center gap-1">
            <Clock size={10} className="text-accent-oracle" />
            <span className={running ? "text-accent-oracle" : ""}>{fmtSeconds(wall)}</span>
            wall · {capturedSeconds}s captured
          </span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto min-h-0 px-3 py-2 space-y-2">
        {/* Idle — nothing has been replayed yet */}
        {!running && !aml.last && (
          <>
            <div className="text-[11px] text-text-secondary leading-snug">
              New financial market transactions are triaged here by the AML Agent.
            </div>
            <div className="text-[11px] text-text-muted leading-snug">
              No live tokens are spent — the run is a recording. Alerts outside the capture fall back to the
              deterministic policy and are handed to a human reviewer.
            </div>
          </>
        )}

        {/* Either the click has not been acknowledged yet, or the page joined
            a sweep already in flight — both read the same from here. */}
        {running && alerts.length === 0 && (
          <div className="flex items-center gap-2 text-[10px] font-mono text-text-muted">
            <LoaderCircle size={10} className="animate-spin text-accent-oracle" />
            waiting for the sweep to stream…
          </div>
        )}

        {/* Running — one card per alert, steps streaming in order */}
        {running && alerts.map((a, i) => (
          <AlertCard key={a.index} alert={a} position={i} total={aml.run?.alertsTotal} />
        ))}

        {/* Finished — totals plus the ledger the run wrote */}
        {!running && aml.last && (
          <>
            <div className="border border-white/5 rounded bg-bg-elev px-3 py-2">
              <div className="flex items-center gap-2 flex-wrap">
                <CircleCheck size={12} className="text-accent-memory shrink-0" />
                <span className="text-[11px] text-text-primary">sweep finished</span>
                <span className="text-[10px] font-mono text-text-muted truncate">{aml.last.run_id}</span>
                <span className="ml-auto text-[10px] font-mono text-text-muted">
                  {fmtClock(aml.last.finished_at)}
                </span>
              </div>
              <div className="grid grid-cols-3 gap-2 mt-2 text-[10px] font-mono">
                <Stat label="alerts" value={totals?.alerts ?? "—"} color="text-text-accent" />
                <Stat label="captured" value={totals?.captured ?? "—"} color="text-accent-memory" />
                <Stat label="fallback" value={totals?.fallback ?? "—"} color="text-accent-sql" />
                <Stat label="model calls" value={totals?.model_calls ?? "—"} color="text-accent-skill" />
                <Stat label="tokens" value={totals?.tokens ?? "—"} color="text-accent-tool" />
                <Stat
                  label="wall vs captured"
                  value={`${fmtSeconds(totals?.seconds)} vs ${capturedSeconds}s`}
                  color="text-accent-oracle"
                />
              </div>
            </div>

            <div className="border border-white/5 rounded bg-bg-elev overflow-hidden">
              <div className="px-3 py-1.5 border-b border-white/5 flex items-center gap-2">
                <span className="text-[10px] uppercase tracking-wider text-text-muted">
                  AGENT.AML_REPLAY
                </span>
                <span className="text-[10px] font-mono text-text-muted">
                  {(aml.last.alerts || []).length} rows
                </span>
              </div>
              <table className="w-full text-[10px] font-mono border-collapse">
                <thead>
                  <tr className="text-text-muted">
                    <th className="text-left px-3 py-1 font-normal border-b border-white/5">customer</th>
                    <th className="text-left px-3 py-1 font-normal border-b border-white/5">typology</th>
                    <th className="text-right px-3 py-1 font-normal border-b border-white/5">exposure</th>
                    <th className="text-left px-3 py-1 font-normal border-b border-white/5">decision</th>
                    <th className="text-left px-3 py-1 font-normal border-b border-white/5">mode</th>
                    <th className="text-left px-3 py-1 font-normal border-b border-white/5">sar reason</th>
                  </tr>
                </thead>
                <tbody>
                  {(aml.last.alerts || []).map((l, i) => {
                    const meta = DECISION_META[l.decision] || DECISION_META.DISMISS;
                    return (
                      <tr key={`${l.customer_id}-${i}`} className="border-b border-white/[0.03]">
                        <td className="px-3 py-1 text-text-primary truncate">
                          {l.customer_name || l.customer_id}
                        </td>
                        <td className="px-3 py-1 text-accent-skill">{l.typology || "—"}</td>
                        <td className="px-3 py-1 text-right text-accent-tool">
                          {fmtExposure(l.exposure_cents)}
                        </td>
                        <td className="px-3 py-1">
                          <span className={meta.color}>{l.decision}</span>
                          {l.confidence != null && (
                            <span className="text-text-muted">
                              {" "}
                              {Math.round((l.confidence <= 1 ? l.confidence * 100 : l.confidence))}%
                            </span>
                          )}
                        </td>
                        <td className="px-3 py-1">
                          <span
                            className={
                              l.mode === "captured" ? "text-accent-memory" : "text-accent-sql"
                            }
                          >
                            {l.mode === "captured" ? "captured" : "fallback → human"}
                          </span>
                        </td>
                        <td className="px-3 py-1 text-accent-tool truncate">{l.sar_reason || "—"}</td>
                      </tr>
                    );
                  })}
                  {(aml.last.alerts || []).length === 0 && (
                    <tr>
                      <td colSpan={6} className="px-3 py-3 text-center text-text-muted italic">
                        no rows in the replayed ledger
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}

        {/* The queue is what remains to be worked — visible whenever the loop
            is not mid-sweep, including after a finished run. */}
        {!running && <QueuePreview queue={queue} />}

        <RecallBlock recall={aml.recall} now={now} onRecall={aml.recallMorning} />
      </div>
    </div>
  );
}
