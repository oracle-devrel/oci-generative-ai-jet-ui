import { useCallback, useEffect, useRef, useState } from "react";

/** Thinking time of the original morning recap — also the fallback when the
 *  server has not announced its own timing yet. */
export const DEFAULT_RECALL_SECONDS = 16.2;

// A sweep the backend never acknowledges (AML replay module missing) must not
// leave the panel stuck on "running…", so the optimistic state self-heals.
const START_GUARD_MS = 10_000;

function newAlert(index, alert) {
  return {
    index,
    alert: alert || null,
    steps: [],
    mode: null,
    decision: null,
    ledger: null,
    elapsed_ms: null,
    tokens: 0,
  };
}

/**
 * Patch one alert inside the live run, allocating its slot when an event
 * arrives before `aml_alert_started` — the UI must never drop a step.
 */
function patchAlert(alerts, index, fn) {
  const at = alerts.findIndex((a) => a.index === index);
  if (at === -1) return [...alerts, fn(newAlert(index))];
  const next = alerts.slice();
  next[at] = fn(next[at]);
  return next;
}

/**
 * Live view of the autonomous AML triage loop.
 *
 * The loop is a *captured* Grok run: the backend replays the exact steps the
 * model took the morning the alerts arrived — context build, tool calls,
 * decision — with the original per-step timings, so the panel can stream the
 * whole triage without spending a live token per alert. Alerts that were not
 * in the capture fall back to the deterministic triage policy and are flagged
 * for a human instead.
 *
 * Events (see the backend replay module):
 *   aml_status          → {state, speed, model, captured_at, last}
 *   aml_queue           → {alerts[…]}           (new FM hits awaiting triage)
 *   aml_sweep_started   → {run_id, started_at, limit, model, captured_at, alerts}
 *   aml_alert_started   → {run_id, index, total, alert}
 *   aml_step            → {run_id, index, step, kind, label, tool, args, planned_ms, capture, detail}
 *   aml_step_finished   → {run_id, index, step, duration_ms, tokens, result_lines}
 *   aml_alert_decided   → {run_id, index, decision, mode, elapsed_ms, tokens}
 *   aml_alert_recorded  → {run_id, index, ledger}
 *   aml_sweep_finished  → {run_id, totals, alerts}
 *   aml_recall_started  → {run_id, seconds, tokens}
 *   aml_recall_finished → {run_id, answer_lines, seconds, tokens}
 */
export function useAmlLoop(socket) {
  const [state, setState] = useState("idle");
  const [status, setStatus] = useState(null);
  const [run, setRun] = useState(null);
  const [last, setLast] = useState(null);
  const [queue, setQueue] = useState([]);
  const [recall, setRecall] = useState(null);

  // True once aml_sweep_started lands; the start guard only fires when the
  // backend never answered the click at all.
  const started = useRef(false);
  const guard = useRef(null);

  useEffect(() => {
    if (!socket) return;

    const onStatus = (p) => {
      if (!p) return;
      setStatus(p);
      if (p.state) {
        setState(p.state);
        if (p.state === "running") started.current = true;
      }
      // The server owns the ledger — it clears `last` on aml_clear — so mirror
      // whatever it reports. A payload without the key leaves ours alone.
      if ("last" in p) setLast(p.last || null);
    };

    const onQueue = (p) => {
      setQueue(Array.isArray(p?.alerts) ? p.alerts : []);
    };

    const onSweepStarted = (p) => {
      if (!p) return;
      started.current = true;
      if (guard.current) window.clearTimeout(guard.current);
      setState("running");
      // Alerts are allocated as aml_alert_started arrives rather than
      // pre-seeded from `p.alerts`: the panels key every step back to the
      // server's alert index, so nothing may assume its numbering.
      setRun({
        run_id: p.run_id,
        started_at: p.started_at || new Date().toISOString(),
        limit: p.limit,
        model: p.model,
        captured_at: p.captured_at,
        alertsTotal: Array.isArray(p.alerts) ? p.alerts.length : 0,
        alerts: [],
      });
    };

    const onAlertStarted = (p) => {
      if (!p) return;
      setRun((r) => {
        if (!r) return r;
        return {
          ...r,
          alertsTotal: p.total || r.alertsTotal,
          alerts: patchAlert(r.alerts, p.index, (a) => ({ ...a, alert: p.alert || a.alert })),
        };
      });
    };

    const onStep = (p) => {
      if (!p) return;
      const step = {
        step: p.step,
        kind: p.kind,
        label: p.label,
        tool: p.tool,
        args: p.args,
        planned_ms: p.planned_ms,
        capture: p.capture,
        detail: p.detail,
        status: "running",
        duration_ms: null,
        tokens: 0,
        result_lines: null,
      };
      setRun((r) => {
        if (!r) return r;
        return {
          ...r,
          alerts: patchAlert(r.alerts, p.index, (a) => {
            const known = a.steps.some((s) => s.step === p.step);
            return {
              ...a,
              steps: known
                ? a.steps.map((s) => (s.step === p.step ? { ...s, ...step } : s))
                : [...a.steps, step],
            };
          }),
        };
      });
    };

    const onStepFinished = (p) => {
      if (!p) return;
      setRun((r) => {
        if (!r) return r;
        return {
          ...r,
          alerts: patchAlert(r.alerts, p.index, (a) => ({
            ...a,
            steps: a.steps.map((s) =>
              s.step === p.step
                ? {
                    ...s,
                    status: "done",
                    duration_ms: p.duration_ms,
                    tokens: p.tokens || 0,
                    result_lines: p.result_lines || null,
                  }
                : s,
            ),
          })),
        };
      });
    };

    const onDecided = (p) => {
      if (!p) return;
      setRun((r) => {
        if (!r) return r;
        return {
          ...r,
          alerts: patchAlert(r.alerts, p.index, (a) => ({
            ...a,
            mode: p.mode,
            decision: p.decision,
            elapsed_ms: p.elapsed_ms,
            tokens: p.tokens || 0,
          })),
        };
      });
    };

    const onRecorded = (p) => {
      if (!p) return;
      setRun((r) => {
        if (!r) return r;
        return {
          ...r,
          alerts: patchAlert(r.alerts, p.index, (a) => ({ ...a, ledger: p.ledger })),
        };
      });
    };

    const onSweepFinished = (p) => {
      started.current = false;
      if (guard.current) window.clearTimeout(guard.current);
      setState("idle");
      if (!p) return;
      setLast({
        run_id: p.run_id,
        finished_at: new Date().toISOString(),
        totals: p.totals,
        alerts: Array.isArray(p.alerts) ? p.alerts : [],
      });
    };

    const onRecallStarted = (p) => {
      setRecall({
        run_id: p?.run_id,
        seconds: p?.seconds ?? DEFAULT_RECALL_SECONDS,
        tokens: p?.tokens ?? 0,
        started_at: new Date().toISOString(),
        running: true,
        answer_lines: [],
      });
    };

    const onRecallFinished = (p) => {
      if (!p) return;
      setRecall({
        run_id: p.run_id,
        seconds: p.seconds ?? DEFAULT_RECALL_SECONDS,
        tokens: p.tokens ?? 0,
        started_at: new Date().toISOString(),
        running: false,
        answer_lines: Array.isArray(p.answer_lines) ? p.answer_lines : [],
      });
    };

    // python-socketio calls event handlers as handler(*args), so requests whose
    // handlers declare no parameter must be emitted WITHOUT a payload (same as
    // live_feed_status_request) or the server raises TypeError.
    const request = () => socket.emit("aml_status_request");

    socket.on("aml_status", onStatus);
    socket.on("aml_queue", onQueue);
    socket.on("aml_sweep_started", onSweepStarted);
    socket.on("aml_alert_started", onAlertStarted);
    socket.on("aml_step", onStep);
    socket.on("aml_step_finished", onStepFinished);
    socket.on("aml_alert_decided", onDecided);
    socket.on("aml_alert_recorded", onRecorded);
    socket.on("aml_sweep_finished", onSweepFinished);
    socket.on("aml_recall_started", onRecallStarted);
    socket.on("aml_recall_finished", onRecallFinished);
    // The server owns the store; re-ask on every (re)connect.
    socket.on("connect", request);
    if (socket.connected) request();

    return () => {
      socket.off("aml_status", onStatus);
      socket.off("aml_queue", onQueue);
      socket.off("aml_sweep_started", onSweepStarted);
      socket.off("aml_alert_started", onAlertStarted);
      socket.off("aml_step", onStep);
      socket.off("aml_step_finished", onStepFinished);
      socket.off("aml_alert_decided", onDecided);
      socket.off("aml_alert_recorded", onRecorded);
      socket.off("aml_sweep_finished", onSweepFinished);
      socket.off("aml_recall_started", onRecallStarted);
      socket.off("aml_recall_finished", onRecallFinished);
      socket.off("connect", request);
    };
  }, [socket]);

  useEffect(() => () => window.clearTimeout(guard.current), []);

  const runSweep = useCallback(
    (limit = 3) => {
      if (!socket) return;
      started.current = false;
      setState("running");
      if (guard.current) window.clearTimeout(guard.current);
      guard.current = window.setTimeout(() => {
        if (!started.current) setState("idle");
      }, START_GUARD_MS);
      socket.emit("aml_sweep_run", { limit });
    },
    [socket],
  );

  const clear = useCallback(() => {
    if (!socket) return;
    started.current = false;
    if (guard.current) window.clearTimeout(guard.current);
    setState("idle");
    setRun(null);
    setLast(null);
    setRecall(null);
    socket.emit("aml_clear");
  }, [socket]);

  const recallMorning = useCallback(() => {
    if (!socket) return;
    setRecall({
      run_id: null,
      seconds: DEFAULT_RECALL_SECONDS,
      tokens: 0,
      started_at: new Date().toISOString(),
      running: true,
      answer_lines: [],
    });
    socket.emit("aml_recall_run");
  }, [socket]);

  return { state, run, last, queue, recall, status, runSweep, clear, recallMorning };
}
