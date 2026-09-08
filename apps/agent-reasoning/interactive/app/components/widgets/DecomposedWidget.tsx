"use client";

import { useState, useCallback, useRef, useEffect } from "react";

/* ------------------------------------------------------------------ */
/*  Types & Data                                                       */
/* ------------------------------------------------------------------ */

type TaskStatus = "pending" | "running" | "complete";

interface SubTask {
  id: number;
  description: string;
  result: string;
}

const QUESTION =
  "Plan a sustainable city transportation system that reduces emissions by 40%";

const SUB_TASKS: SubTask[] = [
  {
    id: 1,
    description: "Analyze current transportation emissions baseline",
    result: "Current: 2.4M tons CO2/year, 60% from personal vehicles",
  },
  {
    id: 2,
    description: "Identify high-impact intervention areas",
    result: "Top 3: electric bus fleet, bike infrastructure, congestion pricing",
  },
  {
    id: 3,
    description: "Design integrated solution with targets",
    result:
      "Phase 1: 200 electric buses, 50km bike lanes, downtown pricing zone",
  },
  {
    id: 4,
    description: "Validate against 40% reduction target",
    result: "Projected reduction: 43.2% \u2014 exceeds target",
  },
];

const SYNTHESIS =
  "Based on sequential analysis: converting 60% of bus fleet to electric, building 50km of protected bike lanes, and implementing downtown congestion pricing will achieve a projected 43.2% emissions reduction \u2014 exceeding the 40% target. The plan phases implementation over 3 years with measurable milestones at each stage.";

/* ------------------------------------------------------------------ */
/*  Status helpers                                                     */
/* ------------------------------------------------------------------ */

const STATUS_COLORS: Record<TaskStatus, { border: string; badge: string; badgeBg: string }> = {
  pending: {
    border: "rgba(161,161,170,0.35)",
    badge: "#a1a1aa",
    badgeBg: "rgba(161,161,170,0.12)",
  },
  running: {
    border: "#a78bfa",
    badge: "#a78bfa",
    badgeBg: "rgba(167,139,250,0.15)",
  },
  complete: {
    border: "#4ade80",
    badge: "#4ade80",
    badgeBg: "rgba(74,222,128,0.12)",
  },
};

const STATUS_LABEL: Record<TaskStatus, string> = {
  pending: "Pending",
  running: "Running\u2026",
  complete: "Complete",
};

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function DecomposedWidget() {
  /* --- Hydration guard -------------------------------------------- */
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  /* --- State ------------------------------------------------------ */
  const [taskStatuses, setTaskStatuses] = useState<TaskStatus[]>(
    SUB_TASKS.map(() => "pending"),
  );
  const [isRunning, setIsRunning] = useState(false);
  const [showDecomposed, setShowDecomposed] = useState(false);
  const [showSynthesis, setShowSynthesis] = useState(false);

  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const stepRef = useRef(0);

  const completedCount = taskStatuses.filter((s) => s === "complete").length;
  const totalTasks = SUB_TASKS.length;
  const progressPct = (completedCount / totalTasks) * 100;

  /* --- Helpers ---------------------------------------------------- */
  const clearTimer = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const reset = useCallback(() => {
    clearTimer();
    stepRef.current = 0;
    setTaskStatuses(SUB_TASKS.map(() => "pending"));
    setIsRunning(false);
    setShowDecomposed(false);
    setShowSynthesis(false);
  }, [clearTimer]);

  /* Sequential execution: set task to running, then after delay mark complete */
  const executeStep = useCallback(() => {
    const idx = stepRef.current;

    if (idx >= totalTasks) {
      /* All tasks done -- show synthesis */
      setIsRunning(false);
      setShowSynthesis(true);
      return;
    }

    /* Mark current task as running */
    setTaskStatuses((prev) => {
      const next = [...prev];
      next[idx] = "running";
      return next;
    });

    /* After delay, mark complete and move to next */
    timerRef.current = setTimeout(() => {
      setTaskStatuses((prev) => {
        const next = [...prev];
        next[idx] = "complete";
        return next;
      });
      stepRef.current = idx + 1;

      /* Schedule next step */
      timerRef.current = setTimeout(() => executeStep(), 200);
    }, 800);
  }, [totalTasks]);

  const handleDecompose = useCallback(() => {
    reset();
    setShowDecomposed(true);
    setIsRunning(true);

    /* Let the task cards animate in first, then begin execution */
    timerRef.current = setTimeout(() => {
      stepRef.current = 0;
      executeStep();
    }, 600);
  }, [reset, executeStep]);

  /* Cleanup on unmount */
  useEffect(() => clearTimer, [clearTimer]);

  /* ---------------------------------------------------------------- */
  /*  Render                                                           */
  /* ---------------------------------------------------------------- */

  if (!mounted) {
    return (
      <div className="widget-container s4">
        <div className="widget-label">
          Interactive &middot; Problem Decomposition
        </div>
        <div style={{ height: 200 }} />
      </div>
    );
  }

  return (
    <div className="widget-container s4">
      <div className="widget-label">
        Interactive &middot; Problem Decomposition
      </div>

      {/* ---- Complex question ---- */}
      <div
        className="rounded-lg"
        style={{
          background: "rgba(255,255,255,0.03)",
          border: "1px solid rgba(255,255,255,0.08)",
          padding: "0.75rem 1rem",
          marginBottom: "1.25rem",
        }}
      >
        <span
          style={{
            display: "block",
            fontFamily: "var(--font-mono), monospace",
            fontSize: "0.7rem",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            color: "#a1a1aa",
            marginBottom: "0.35rem",
          }}
        >
          Complex Problem
        </span>
        <p style={{ color: "#e4e4e7", margin: 0, lineHeight: 1.7 }}>
          {QUESTION}
        </p>
      </div>

      {/* ---- Controls ---- */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0.5rem",
          marginBottom: "1.25rem",
          flexWrap: "wrap",
        }}
      >
        <button
          className="btn-mono"
          onClick={handleDecompose}
          disabled={isRunning}
          style={{
            background: isRunning
              ? "transparent"
              : "rgba(167,139,250,0.12)",
            borderColor: isRunning
              ? "rgba(255,255,255,0.08)"
              : "rgba(167,139,250,0.35)",
            color: isRunning ? "#a1a1aa" : "#a78bfa",
            cursor: isRunning ? "not-allowed" : "pointer",
          }}
        >
          {isRunning ? "Solving\u2026" : "Decompose"}
        </button>

        <button className="btn-mono" onClick={reset}>
          Reset
        </button>

        {showDecomposed && (
          <span
            style={{
              fontFamily: "var(--font-mono), monospace",
              fontSize: "0.72rem",
              color: "#a1a1aa",
              marginLeft: "auto",
            }}
          >
            {completedCount}/{totalTasks} sub-tasks
          </span>
        )}
      </div>

      {/* ---- Progress bar ---- */}
      {showDecomposed && (
        <div
          style={{
            height: 4,
            background: "rgba(255,255,255,0.06)",
            borderRadius: 2,
            marginBottom: "1.25rem",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              height: "100%",
              width: `${progressPct}%`,
              borderRadius: 2,
              background:
                completedCount === totalTasks
                  ? "linear-gradient(90deg, #a78bfa, #c4b5fd)"
                  : "rgba(167,139,250,0.6)",
              transition: "width 0.4s ease-out",
            }}
          />
        </div>
      )}

      {/* ---- Task list ---- */}
      {showDecomposed && (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "0.6rem",
            marginBottom: "1.25rem",
          }}
        >
          {SUB_TASKS.map((task, i) => {
            const status = taskStatuses[i];
            const colors = STATUS_COLORS[status];

            return (
              <div
                key={task.id}
                className="animate-slide-in"
                style={{
                  animationDelay: `${i * 0.1}s`,
                  background:
                    status === "complete"
                      ? "rgba(74,222,128,0.04)"
                      : status === "running"
                        ? "rgba(167,139,250,0.05)"
                        : "rgba(255,255,255,0.02)",
                  border: "1px solid rgba(255,255,255,0.08)",
                  borderLeftWidth: 3,
                  borderLeftColor: colors.border,
                  borderRadius: 8,
                  padding: "0.75rem 1rem",
                  transition:
                    "background 0.3s ease, border-left-color 0.3s ease",
                }}
              >
                {/* Header: task number + description + badge */}
                <div
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    justifyContent: "space-between",
                    gap: "0.75rem",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "baseline",
                      gap: "0.5rem",
                      flex: 1,
                      minWidth: 0,
                    }}
                  >
                    <span
                      style={{
                        fontFamily: "var(--font-mono), monospace",
                        fontSize: "0.68rem",
                        fontWeight: 700,
                        color: "#a78bfa",
                        letterSpacing: "0.04em",
                        flexShrink: 0,
                      }}
                    >
                      #{task.id}
                    </span>
                    <span
                      style={{
                        fontSize: "0.85rem",
                        color: "#e4e4e7",
                        lineHeight: 1.5,
                      }}
                    >
                      {task.description}
                    </span>
                  </div>

                  {/* Status badge */}
                  <span
                    style={{
                      fontFamily: "var(--font-mono), monospace",
                      fontSize: "0.6rem",
                      fontWeight: 600,
                      letterSpacing: "0.06em",
                      textTransform: "uppercase",
                      padding: "0.15rem 0.5rem",
                      borderRadius: "9999px",
                      background: colors.badgeBg,
                      color: colors.badge,
                      flexShrink: 0,
                      whiteSpace: "nowrap",
                    }}
                  >
                    {STATUS_LABEL[status]}
                  </span>
                </div>

                {/* Result (visible when complete) */}
                {status === "complete" && (
                  <div
                    style={{
                      marginTop: "0.5rem",
                      paddingTop: "0.5rem",
                      borderTop: "1px solid rgba(255,255,255,0.06)",
                    }}
                  >
                    <span
                      style={{
                        fontFamily: "var(--font-mono), monospace",
                        fontSize: "0.65rem",
                        color: "#a1a1aa",
                        textTransform: "uppercase",
                        letterSpacing: "0.06em",
                      }}
                    >
                      Result
                    </span>
                    <p
                      style={{
                        margin: "0.25rem 0 0",
                        fontSize: "0.82rem",
                        color: "#c4b5fd",
                        lineHeight: 1.55,
                        fontFamily: "var(--font-mono), monospace",
                      }}
                    >
                      {task.result}
                    </p>
                  </div>
                )}

                {/* Running indicator */}
                {status === "running" && (
                  <div
                    style={{
                      marginTop: "0.5rem",
                      height: 2,
                      borderRadius: 1,
                      overflow: "hidden",
                      background: "rgba(167,139,250,0.15)",
                    }}
                  >
                    <div
                      style={{
                        height: "100%",
                        width: "60%",
                        borderRadius: 1,
                        background: "#a78bfa",
                        animation: "pulseBar 1.2s ease-in-out infinite",
                      }}
                    />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* ---- Placeholder when idle ---- */}
      {!showDecomposed && (
        <div
          className="rounded-lg"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            height: 80,
            border: "1px dashed rgba(255,255,255,0.1)",
            color: "#a1a1aa",
            fontFamily: "var(--font-mono), monospace",
            fontSize: "0.78rem",
          }}
        >
          Press &ldquo;Decompose&rdquo; to break into sub-tasks
        </div>
      )}

      {/* ---- Synthesis panel ---- */}
      {showSynthesis && (
        <div
          className="animate-slide-in"
          style={{
            background: "rgba(167,139,250,0.06)",
            border: "1px solid rgba(167,139,250,0.25)",
            borderLeftWidth: 3,
            borderLeftColor: "#a78bfa",
            borderRadius: 8,
            padding: "0.85rem 1rem",
            boxShadow: "0 0 18px rgba(167,139,250,0.12)",
          }}
        >
          <span
            style={{
              display: "block",
              fontFamily: "var(--font-mono), monospace",
              fontSize: "0.68rem",
              fontWeight: 700,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              color: "#a78bfa",
              marginBottom: "0.45rem",
            }}
          >
            Synthesized Answer
          </span>
          <p
            style={{
              margin: 0,
              fontSize: "0.85rem",
              color: "#e4e4e7",
              lineHeight: 1.65,
            }}
          >
            {SYNTHESIS}
          </p>
        </div>
      )}

      {/* ---- Inline keyframe for running indicator ---- */}
      <style
        dangerouslySetInnerHTML={{
          __html: `
@keyframes pulseBar {
  0%, 100% { transform: translateX(-40%); opacity: 0.6; }
  50% { transform: translateX(80%); opacity: 1; }
}`,
        }}
      />
    </div>
  );
}
