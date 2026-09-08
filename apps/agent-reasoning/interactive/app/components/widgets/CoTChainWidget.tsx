"use client";

import { useState, useCallback, useRef, useEffect } from "react";

/* ------------------------------------------------------------------ */
/*  Data                                                               */
/* ------------------------------------------------------------------ */

interface Step {
  label: string;
  text: string;
}

interface Problem {
  id: string;
  title: string;
  question: string;
  steps: Step[];
  directAnswer: string;
  directCorrect: boolean;
}

const PROBLEMS: Problem[] = [
  {
    id: "fruits",
    title: "Fruit Boxes",
    question:
      "If a store has 3 boxes with 12 apples each, and 2 boxes with 8 oranges each, how many total fruits are there?",
    steps: [
      { label: "Step 1", text: "Calculate apples: 3 boxes \u00d7 12 apples = 36 apples" },
      { label: "Step 2", text: "Calculate oranges: 2 boxes \u00d7 8 oranges = 16 oranges" },
      { label: "Step 3", text: "Add totals: 36 + 16 = 52 fruits" },
      { label: "Step 4", text: "Final Answer: 52 fruits" },
    ],
    directAnswer: "48 fruits",
    directCorrect: false,
  },
  {
    id: "trains",
    title: "Train Problem",
    question:
      "Two trains leave stations 300 km apart, heading toward each other at 60 km/h and 90 km/h. How long until they meet?",
    steps: [
      { label: "Step 1", text: "Combined speed: 60 + 90 = 150 km/h" },
      { label: "Step 2", text: "Time = Distance \u00f7 Speed = 300 \u00f7 150" },
      { label: "Step 3", text: "300 \u00f7 150 = 2 hours" },
      { label: "Step 4", text: "Final Answer: 2 hours" },
    ],
    directAnswer: "3 hours",
    directCorrect: false,
  },
  {
    id: "discount",
    title: "Compound Discount",
    question:
      "A jacket costs $120. It\u2019s 25% off, then an extra 10% off the sale price. What is the final price?",
    steps: [
      { label: "Step 1", text: "First discount: $120 \u00d7 0.25 = $30 off \u2192 $90" },
      { label: "Step 2", text: "Second discount: $90 \u00d7 0.10 = $9 off" },
      { label: "Step 3", text: "Final price: $90 \u2212 $9 = $81" },
      { label: "Step 4", text: "Final Answer: $81" },
    ],
    directAnswer: "$78",
    directCorrect: false,
  },
];

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function CoTChainWidget() {
  /* --- Hydration guard -------------------------------------------- */
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  /* --- State ------------------------------------------------------ */
  const [problemIdx, setProblemIdx] = useState(0);
  const [visibleSteps, setVisibleSteps] = useState(0);
  const [isRunning, setIsRunning] = useState(false);
  const [autoPlay, setAutoPlay] = useState(false);
  const [showDirect, setShowDirect] = useState(false);

  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const problem = PROBLEMS[problemIdx];
  const totalSteps = problem.steps.length;

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
    setShowDirect(false);
  }, [clearTimer]);

  const revealNext = useCallback(() => {
    setVisibleSteps((prev) => {
      const next = prev + 1;
      if (next >= totalSteps) {
        setIsRunning(false);
        setShowDirect(true);
        return next;
      }
      /* schedule the following step */
      timerRef.current = setTimeout(() => revealNext(), 500);
      return next;
    });
  }, [totalSteps]);

  const runCoT = useCallback(() => {
    reset();
    setIsRunning(true);
    /* kick off the first reveal after a brief pause */
    timerRef.current = setTimeout(() => revealNext(), 350);
  }, [reset, revealNext]);

  /* Auto-play on problem change */
  useEffect(() => {
    if (autoPlay) {
      runCoT();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [problemIdx, autoPlay]);

  /* Cleanup on unmount */
  useEffect(() => clearTimer, [clearTimer]);

  const handleProblemSwitch = useCallback(
    (idx: number) => {
      if (idx === problemIdx) return;
      clearTimer();
      setVisibleSteps(0);
      setIsRunning(false);
      setShowDirect(false);
      setProblemIdx(idx);
    },
    [problemIdx, clearTimer],
  );

  /* ---------------------------------------------------------------- */
  /*  Render                                                           */
  /* ---------------------------------------------------------------- */

  return (
    <div className="widget-container s1">
      <div className="widget-label">Interactive &middot; Chain-of-Thought Reasoning</div>

      {/* ---- Problem selector ---- */}
      <div className="flex flex-wrap items-center gap-2 mb-5">
        {PROBLEMS.map((p, i) => (
          <button
            key={p.id}
            onClick={() => handleProblemSwitch(i)}
            className={`btn-mono ${i === problemIdx ? "active" : ""}`}
          >
            {p.title}
          </button>
        ))}
      </div>

      {/* ---- Question ---- */}
      <div
        className="rounded-lg p-4 mb-6"
        style={{
          background: "rgba(255,255,255,0.03)",
          border: "1px solid rgba(255,255,255,0.08)",
        }}
      >
        <span
          className="block mb-1"
          style={{
            fontFamily: "var(--font-mono), monospace",
            fontSize: "0.7rem",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            color: "#a1a1aa",
          }}
        >
          Problem
        </span>
        <p style={{ color: "#e4e4e7", margin: 0, lineHeight: 1.7 }}>
          {problem.question}
        </p>
      </div>

      {/* ---- Controls ---- */}
      <div className="flex flex-wrap items-center gap-3 mb-6">
        <button
          className="btn-mono"
          onClick={runCoT}
          disabled={isRunning}
          style={{
            background: isRunning ? "transparent" : "rgba(249,115,22,0.12)",
            borderColor: isRunning
              ? "rgba(255,255,255,0.08)"
              : "rgba(249,115,22,0.35)",
            color: isRunning ? "#a1a1aa" : "#f97316",
            cursor: isRunning ? "not-allowed" : "pointer",
          }}
        >
          {isRunning ? "Running\u2026" : "Run CoT"}
        </button>

        <button className="btn-mono" onClick={reset}>
          Reset
        </button>

        <label
          className="flex items-center gap-2 select-none"
          style={{
            fontFamily: "var(--font-mono), monospace",
            fontSize: "0.78rem",
            color: "#a1a1aa",
            cursor: "pointer",
          }}
        >
          <span
            role="checkbox"
            aria-checked={autoPlay}
            tabIndex={0}
            onClick={() => setAutoPlay((v) => !v)}
            onKeyDown={(e) => {
              if (e.key === " " || e.key === "Enter") {
                e.preventDefault();
                setAutoPlay((v) => !v);
              }
            }}
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              width: 16,
              height: 16,
              borderRadius: 4,
              border: `1px solid ${
                autoPlay ? "rgba(249,115,22,0.5)" : "rgba(255,255,255,0.15)"
              }`,
              background: autoPlay
                ? "rgba(249,115,22,0.15)"
                : "transparent",
              transition: "all 0.15s",
            }}
          >
            {autoPlay && (
              <span style={{ color: "#f97316", fontSize: 11, lineHeight: 1 }}>
                &#10003;
              </span>
            )}
          </span>
          Auto Play
        </label>
      </div>

      {/* ---- Main area: CoT steps + Direct answer ---- */}
      <div className="flex flex-col lg:flex-row gap-6">
        {/* -- CoT column -- */}
        <div className="flex-1 min-w-0">
          <span
            className="block mb-3"
            style={{
              fontFamily: "var(--font-mono), monospace",
              fontSize: "0.7rem",
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              color: "#f97316",
              fontWeight: 600,
            }}
          >
            Chain-of-Thought
          </span>

          <div className="flex flex-col gap-0">
            {problem.steps.map((step, i) => {
              const visible = i < visibleSteps;
              const isFinal = i === totalSteps - 1;

              return (
                <div key={`${problem.id}-${i}`}>
                  {/* Step card */}
                  <div
                    className={visible ? "animate-fade-in" : ""}
                    style={{
                      opacity: visible ? 1 : 0,
                      transform: visible
                        ? "translateY(0)"
                        : "translateY(10px)",
                      transition: "opacity 0.45s ease-out, transform 0.45s ease-out",
                      borderLeft: `3px solid ${
                        isFinal && visible ? "#f97316" : "rgba(249,115,22,0.45)"
                      }`,
                      background:
                        isFinal && visible
                          ? "rgba(249,115,22,0.07)"
                          : "rgba(255,255,255,0.03)",
                      border:
                        isFinal && visible
                          ? "1px solid rgba(249,115,22,0.25)"
                          : "1px solid rgba(255,255,255,0.08)",
                      borderLeftWidth: 3,
                      borderLeftColor:
                        isFinal && visible
                          ? "#f97316"
                          : "rgba(249,115,22,0.45)",
                      borderRadius: 8,
                      padding: "0.75rem 1rem",
                      boxShadow:
                        isFinal && visible
                          ? "0 0 18px rgba(249,115,22,0.15)"
                          : "none",
                    }}
                  >
                    <span
                      style={{
                        fontFamily: "var(--font-mono), monospace",
                        fontSize: "0.68rem",
                        textTransform: "uppercase",
                        letterSpacing: "0.06em",
                        color: isFinal && visible ? "#f97316" : "#a1a1aa",
                        fontWeight: 600,
                      }}
                    >
                      {step.label}
                    </span>
                    <p
                      style={{
                        color: "#e4e4e7",
                        margin: "0.35rem 0 0",
                        fontSize: "0.88rem",
                        lineHeight: 1.55,
                      }}
                    >
                      {step.text}
                    </p>
                  </div>

                  {/* Arrow connector (skip after last step) */}
                  {i < totalSteps - 1 && (
                    <div
                      className="flex justify-center"
                      style={{
                        height: 28,
                        opacity: visible ? 1 : 0,
                        transition: "opacity 0.3s",
                      }}
                    >
                      {mounted && (
                        <svg
                          width="16"
                          height="28"
                          viewBox="0 0 16 28"
                          fill="none"
                          xmlns="http://www.w3.org/2000/svg"
                        >
                          <line
                            x1="8"
                            y1="0"
                            x2="8"
                            y2="20"
                            stroke="rgba(249,115,22,0.35)"
                            strokeWidth="1.5"
                          />
                          <path
                            d="M4 16 L8 22 L12 16"
                            stroke="rgba(249,115,22,0.5)"
                            strokeWidth="1.5"
                            fill="none"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                        </svg>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Placeholder when nothing is running */}
          {visibleSteps === 0 && !isRunning && (
            <div
              className="rounded-lg flex items-center justify-center"
              style={{
                height: 80,
                border: "1px dashed rgba(255,255,255,0.1)",
                color: "#a1a1aa",
                fontFamily: "var(--font-mono), monospace",
                fontSize: "0.78rem",
              }}
            >
              Press &ldquo;Run CoT&rdquo; to begin
            </div>
          )}
        </div>

        {/* -- Direct answer column -- */}
        <div
          className="lg:w-[280px] shrink-0"
          style={{
            opacity: showDirect ? 1 : 0.35,
            transition: "opacity 0.5s",
          }}
        >
          <span
            className="block mb-3"
            style={{
              fontFamily: "var(--font-mono), monospace",
              fontSize: "0.7rem",
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              color: "#a1a1aa",
              fontWeight: 600,
            }}
          >
            Direct Answer (No CoT)
          </span>

          <div
            className={showDirect ? "animate-slide-in" : ""}
            style={{
              background: "rgba(255,255,255,0.03)",
              border: `1px solid ${
                showDirect
                  ? problem.directCorrect
                    ? "rgba(74,222,128,0.3)"
                    : "rgba(244,63,94,0.3)"
                  : "rgba(255,255,255,0.08)"
              }`,
              borderRadius: 8,
              padding: "0.85rem 1rem",
            }}
          >
            <p
              style={{
                fontFamily: "var(--font-mono), monospace",
                fontSize: "0.85rem",
                color: showDirect
                  ? problem.directCorrect
                    ? "#4ade80"
                    : "#f43f5e"
                  : "#a1a1aa",
                margin: 0,
                lineHeight: 1.6,
              }}
            >
              {showDirect ? problem.directAnswer : "\u2014"}
            </p>
            {showDirect && (
              <span
                className="animate-fade-in"
                style={{
                  display: "inline-block",
                  marginTop: 8,
                  fontFamily: "var(--font-mono), monospace",
                  fontSize: "0.68rem",
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                  color: problem.directCorrect ? "#4ade80" : "#f43f5e",
                  fontWeight: 600,
                }}
              >
                {problem.directCorrect ? "\u2713 Correct" : "\u2717 Incorrect"}
              </span>
            )}
          </div>

          {showDirect && (
            <p
              className="animate-fade-in"
              style={{
                marginTop: 12,
                fontSize: "0.78rem",
                color: "#a1a1aa",
                lineHeight: 1.6,
              }}
            >
              Without step-by-step reasoning, the model jumps straight to an
              answer and often makes arithmetic or logical errors.
            </p>
          )}
        </div>
      </div>

      {/* ---- Progress indicator ---- */}
      <div className="mt-6 flex items-center gap-3">
        <span
          style={{
            fontFamily: "var(--font-mono), monospace",
            fontSize: "0.7rem",
            color: "#a1a1aa",
          }}
        >
          {visibleSteps}/{totalSteps} steps
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
                  ? "#f97316"
                  : "rgba(249,115,22,0.5)",
              transition: "width 0.35s ease-out",
            }}
          />
        </div>
      </div>
    </div>
  );
}
