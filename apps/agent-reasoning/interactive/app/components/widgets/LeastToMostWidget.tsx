"use client";

import { useState, useCallback, useRef, useEffect } from "react";

/* ------------------------------------------------------------------ */
/*  Data                                                               */
/* ------------------------------------------------------------------ */

interface SubProblem {
  level: number;
  difficulty: "Easy" | "Medium" | "Hard" | "Hardest";
  question: string;
  answer: string;
}

const PROBLEM =
  "If it takes 5 machines 5 minutes to make 5 widgets, how long would it take 100 machines to make 100 widgets?";

const SUB_PROBLEMS: SubProblem[] = [
  {
    level: 1,
    difficulty: "Easy",
    question: "How many widgets does 1 machine make in 5 minutes?",
    answer: "1 widget",
  },
  {
    level: 2,
    difficulty: "Medium",
    question: "What is the rate per machine?",
    answer: "1 widget per 5 minutes",
  },
  {
    level: 3,
    difficulty: "Hard",
    question: "How many widgets do 100 machines make in 5 minutes?",
    answer: "100 widgets",
  },
  {
    level: 4,
    difficulty: "Hardest",
    question: "So how long for 100 machines to make 100 widgets?",
    answer: "5 minutes",
  },
];

/* ------------------------------------------------------------------ */
/*  Color helpers                                                      */
/* ------------------------------------------------------------------ */

/** Gradient from light purple (easy) to deep purple (hardest) */
function stepColor(level: number): {
  bg: string;
  border: string;
  text: string;
  glow: string;
} {
  const palette = [
    {
      bg: "rgba(196,181,253,0.08)",
      border: "rgba(196,181,253,0.35)",
      text: "#c4b5fd",
      glow: "rgba(196,181,253,0.12)",
    },
    {
      bg: "rgba(167,139,250,0.10)",
      border: "rgba(167,139,250,0.40)",
      text: "#a78bfa",
      glow: "rgba(167,139,250,0.15)",
    },
    {
      bg: "rgba(139,92,246,0.12)",
      border: "rgba(139,92,246,0.45)",
      text: "#8b5cf6",
      glow: "rgba(139,92,246,0.18)",
    },
    {
      bg: "rgba(109,40,217,0.14)",
      border: "rgba(109,40,217,0.50)",
      text: "#7c3aed",
      glow: "rgba(109,40,217,0.22)",
    },
  ];
  return palette[Math.min(level - 1, palette.length - 1)];
}

function difficultyBadge(difficulty: SubProblem["difficulty"]): {
  bg: string;
  color: string;
} {
  switch (difficulty) {
    case "Easy":
      return { bg: "rgba(74,222,128,0.12)", color: "#4ade80" };
    case "Medium":
      return { bg: "rgba(250,204,21,0.12)", color: "#facc15" };
    case "Hard":
      return { bg: "rgba(249,115,22,0.12)", color: "#fb923c" };
    case "Hardest":
      return { bg: "rgba(244,63,94,0.12)", color: "#f43f5e" };
  }
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function LeastToMostWidget() {
  /* --- Hydration guard -------------------------------------------- */
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  /* --- State ------------------------------------------------------ */
  const [visibleSteps, setVisibleSteps] = useState(0);
  const [isRunning, setIsRunning] = useState(false);
  const [showComparison, setShowComparison] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const totalSteps = SUB_PROBLEMS.length;

  /* --- Helpers ---------------------------------------------------- */
  const clearTimer = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const reset = useCallback(() => {
    clearTimer();
    setVisibleSteps(0);
    setIsRunning(false);
    setShowComparison(false);
  }, [clearTimer]);

  const revealNext = useCallback(() => {
    setVisibleSteps((prev) => {
      const next = prev + 1;
      if (next >= totalSteps) {
        setIsRunning(false);
        setShowComparison(true);
        return next;
      }
      timerRef.current = setTimeout(() => revealNext(), 500);
      return next;
    });
  }, [totalSteps]);

  const solve = useCallback(() => {
    reset();
    setIsRunning(true);
    timerRef.current = setTimeout(() => revealNext(), 350);
  }, [reset, revealNext]);

  /* Cleanup on unmount */
  useEffect(() => clearTimer, [clearTimer]);

  /* ---------------------------------------------------------------- */
  /*  Render                                                           */
  /* ---------------------------------------------------------------- */

  return (
    <div className="widget-container s4">
      <div className="widget-label">
        Interactive &middot; Least-to-Most Prompting
      </div>

      {/* ---- Problem ---- */}
      <div
        className="rounded-lg p-4 mb-6"
        style={{
          background: "rgba(167,139,250,0.06)",
          border: "1px solid rgba(167,139,250,0.15)",
        }}
      >
        <span
          className="block mb-1"
          style={{
            fontFamily: "var(--font-mono), monospace",
            fontSize: "0.7rem",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            color: "#a78bfa",
            fontWeight: 600,
          }}
        >
          Problem
        </span>
        <p style={{ color: "#e4e4e7", margin: 0, lineHeight: 1.7 }}>
          {PROBLEM}
        </p>
      </div>

      {/* ---- Approach label ---- */}
      <div
        style={{
          fontFamily: "var(--font-mono), monospace",
          fontSize: "0.7rem",
          textTransform: "uppercase",
          letterSpacing: "0.08em",
          color: "#a1a1aa",
          marginBottom: "0.5rem",
        }}
      >
        Decompose: easy &rarr; hard, solve progressively
      </div>

      {/* ---- Controls ---- */}
      <div className="flex flex-wrap items-center gap-3 mb-6">
        <button
          className="btn-mono"
          onClick={solve}
          disabled={isRunning}
          style={{
            background: isRunning ? "transparent" : "rgba(167,139,250,0.12)",
            borderColor: isRunning
              ? "rgba(255,255,255,0.08)"
              : "rgba(167,139,250,0.35)",
            color: isRunning ? "#a1a1aa" : "#c4b5fd",
            cursor: isRunning ? "not-allowed" : "pointer",
          }}
        >
          {isRunning ? "Solving\u2026" : "Solve"}
        </button>

        <button className="btn-mono" onClick={reset}>
          Reset
        </button>

        <span
          style={{
            fontFamily: "var(--font-mono), monospace",
            fontSize: "0.7rem",
            color: "#a1a1aa",
          }}
        >
          {visibleSteps}/{totalSteps} sub-problems
        </span>
      </div>

      {/* ---- Staircase visualization ---- */}
      <div
        style={{
          position: "relative",
          minHeight: 320,
        }}
      >
        {/* Placeholder when idle */}
        {visibleSteps === 0 && !isRunning && (
          <div
            className="rounded-lg flex items-center justify-center"
            style={{
              height: 120,
              border: "1px dashed rgba(255,255,255,0.1)",
              color: "#a1a1aa",
              fontFamily: "var(--font-mono), monospace",
              fontSize: "0.78rem",
            }}
          >
            Press &ldquo;Solve&rdquo; to decompose and solve step by step
          </div>
        )}

        {/* Vertical staircase layout: each step indented further right */}
        {(visibleSteps > 0 || isRunning) && (
          <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
            {SUB_PROBLEMS.map((sub, i) => {
              const visible = i < visibleSteps;
              const colors = stepColor(sub.level);
              const badge = difficultyBadge(sub.difficulty);
              const isFinal = i === totalSteps - 1;
              const borderLeftWidth = 3 + i;

              return (
                <div key={`step-${i}`}>
                  {/* Step card */}
                  <div
                    className={visible ? "animate-fade-in" : ""}
                    style={{
                      opacity: visible ? 1 : 0,
                      transform: visible
                        ? "translateY(0)"
                        : "translateY(16px)",
                      transition:
                        "opacity 0.45s ease-out, transform 0.45s ease-out",
                      marginLeft: i * 24,
                      background: isFinal && visible ? colors.bg : "rgba(255,255,255,0.03)",
                      border: `1px solid ${
                        isFinal && visible ? colors.border : "rgba(255,255,255,0.08)"
                      }`,
                      borderLeftWidth: borderLeftWidth,
                      borderLeftColor: visible ? colors.text : "rgba(255,255,255,0.08)",
                      borderLeftStyle: "solid",
                      borderRadius: 8,
                      padding: "0.75rem 1rem",
                      boxShadow:
                        isFinal && visible
                          ? `0 0 20px ${colors.glow}`
                          : "none",
                      position: "relative",
                    }}
                  >
                    {/* Top row: level + difficulty badge */}
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        marginBottom: 6,
                      }}
                    >
                      <span
                        style={{
                          fontFamily: "var(--font-mono), monospace",
                          fontSize: "0.65rem",
                          textTransform: "uppercase",
                          letterSpacing: "0.06em",
                          color: colors.text,
                          fontWeight: 600,
                        }}
                      >
                        Level {sub.level}
                      </span>
                      <span
                        style={{
                          display: "inline-block",
                          fontSize: "0.58rem",
                          fontFamily: "var(--font-mono), monospace",
                          fontWeight: 600,
                          letterSpacing: "0.06em",
                          background: badge.bg,
                          color: badge.color,
                          padding: "1px 7px",
                          borderRadius: 999,
                        }}
                      >
                        {sub.difficulty.toUpperCase()}
                      </span>
                    </div>

                    {/* Sub-question */}
                    <p
                      style={{
                        color: "#e4e4e7",
                        margin: "0 0 4px",
                        fontSize: "0.85rem",
                        lineHeight: 1.55,
                      }}
                    >
                      {sub.question}
                    </p>

                    {/* Answer */}
                    {visible && (
                      <div
                        className="animate-fade-in"
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 6,
                          marginTop: 4,
                          background: isFinal
                            ? "rgba(109,40,217,0.15)"
                            : "rgba(255,255,255,0.04)",
                          border: `1px solid ${
                            isFinal ? colors.border : "rgba(255,255,255,0.06)"
                          }`,
                          borderRadius: 6,
                          padding: "3px 10px",
                        }}
                      >
                        <span
                          style={{
                            fontFamily: "var(--font-mono), monospace",
                            fontSize: "0.72rem",
                            color: "#a1a1aa",
                            fontWeight: 600,
                          }}
                        >
                          &rarr;
                        </span>
                        <span
                          style={{
                            fontFamily: "var(--font-mono), monospace",
                            fontSize: "0.8rem",
                            color: isFinal ? "#c4b5fd" : "#e4e4e7",
                            fontWeight: isFinal ? 700 : 500,
                          }}
                        >
                          {sub.answer}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Arrow connector between steps */}
                  {i < totalSteps - 1 && (
                    <div
                      style={{
                        marginLeft: i * 24 + 20,
                        height: 28,
                        opacity: visible ? 1 : 0,
                        transition: "opacity 0.3s",
                        display: "flex",
                        alignItems: "center",
                        gap: 4,
                      }}
                    >
                      {mounted && (
                        <>
                          <svg
                            width="20"
                            height="28"
                            viewBox="0 0 20 28"
                            fill="none"
                            xmlns="http://www.w3.org/2000/svg"
                          >
                            {/* Diagonal arrow going down-right to mimic staircase */}
                            <line
                              x1="4"
                              y1="2"
                              x2="16"
                              y2="18"
                              stroke={stepColor(sub.level).text}
                              strokeWidth="1.5"
                              opacity={0.5}
                            />
                            <path
                              d="M12 15 L16 20 L10 18"
                              stroke={stepColor(sub.level + 1).text}
                              strokeWidth="1.5"
                              fill="none"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              opacity={0.6}
                            />
                          </svg>
                          <span
                            style={{
                              fontFamily: "var(--font-mono), monospace",
                              fontSize: "0.58rem",
                              color: "#a1a1aa",
                              opacity: 0.5,
                            }}
                          >
                            feeds into
                          </span>
                        </>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ---- Progress bar ---- */}
      <div className="mt-6 flex items-center gap-3">
        <span
          style={{
            fontFamily: "var(--font-mono), monospace",
            fontSize: "0.7rem",
            color: "#a1a1aa",
          }}
        >
          {visibleSteps}/{totalSteps}
        </span>
        <div
          style={{
            flex: 1,
            height: 4,
            borderRadius: 2,
            background: "rgba(255,255,255,0.06)",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              width: `${(visibleSteps / totalSteps) * 100}%`,
              height: "100%",
              borderRadius: 2,
              background:
                visibleSteps === totalSteps
                  ? "#a78bfa"
                  : "rgba(167,139,250,0.5)",
              transition: "width 0.35s ease-out",
            }}
          />
        </div>
      </div>

      {/* ---- Comparison note (wrong answer) ---- */}
      {showComparison && (
        <div
          className="animate-fade-in"
          style={{
            marginTop: "1rem",
            display: "flex",
            gap: "1rem",
            flexWrap: "wrap",
          }}
        >
          {/* Correct answer highlight */}
          <div
            style={{
              flex: 1,
              minWidth: 200,
              padding: "0.75rem 1rem",
              background: "rgba(74,222,128,0.04)",
              border: "1px solid rgba(74,222,128,0.15)",
              borderRadius: 8,
            }}
          >
            <span
              style={{
                display: "block",
                fontFamily: "var(--font-mono), monospace",
                fontSize: "0.62rem",
                textTransform: "uppercase",
                letterSpacing: "0.06em",
                color: "#4ade80",
                fontWeight: 600,
                marginBottom: 4,
              }}
            >
              &#10003; Least-to-Most Answer
            </span>
            <span
              style={{
                fontFamily: "var(--font-mono), monospace",
                fontSize: "0.85rem",
                color: "#e4e4e7",
                fontWeight: 600,
              }}
            >
              5 minutes
            </span>
            <p
              style={{
                margin: "6px 0 0",
                fontSize: "0.75rem",
                color: "#a1a1aa",
                lineHeight: 1.55,
              }}
            >
              Each machine independently makes 1 widget in 5 minutes. With 100
              machines working in parallel, 100 widgets are produced in the same
              5 minutes.
            </p>
          </div>

          {/* Wrong answer */}
          <div
            style={{
              flex: 1,
              minWidth: 200,
              padding: "0.75rem 1rem",
              background: "rgba(244,63,94,0.04)",
              border: "1px solid rgba(244,63,94,0.15)",
              borderRadius: 8,
            }}
          >
            <span
              style={{
                display: "block",
                fontFamily: "var(--font-mono), monospace",
                fontSize: "0.62rem",
                textTransform: "uppercase",
                letterSpacing: "0.06em",
                color: "#f43f5e",
                fontWeight: 600,
                marginBottom: 4,
              }}
            >
              &#10007; Common Wrong Answer
            </span>
            <span
              style={{
                fontFamily: "var(--font-mono), monospace",
                fontSize: "0.85rem",
                color: "#e4e4e7",
                fontWeight: 600,
              }}
            >
              100 minutes
            </span>
            <p
              style={{
                margin: "6px 0 0",
                fontSize: "0.75rem",
                color: "#a1a1aa",
                lineHeight: 1.55,
              }}
            >
              Linear scaling fallacy &mdash; assuming time scales linearly
              with quantity, ignoring that machines work in parallel.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
