"use client";

import { useState, useCallback, useMemo, useEffect } from "react";

/* ------------------------------------------------------------------ */
/*  Data                                                               */
/* ------------------------------------------------------------------ */

type DatasetKey = "gsm8k" | "mmlu" | "arc-c";

interface StrategyEntry {
  name: string;
  score: number;
  calls: number; // estimated LLM calls per query
}

/* Real benchmark data from qwen3.5:9b (9.7B Q4_K_M), March 2026.
   4,200 evaluations across 13 strategies. */
const DATASETS: Record<DatasetKey, { label: string; description: string; entries: StrategyEntry[] }> = {
  gsm8k: {
    label: "GSM8K",
    description: "Grade-school math reasoning",
    entries: [
      { name: "Recursive", score: 96, calls: 6 },
      { name: "Tree of Thoughts", score: 96, calls: 7 },
      { name: "Standard", score: 96, calls: 1 },
      { name: "Self-Reflection", score: 96, calls: 3 },
      { name: "Chain of Thought", score: 94, calls: 1 },
      { name: "Refinement Loop", score: 94, calls: 8 },
      { name: "Self-Consistency", score: 92, calls: 5 },
      { name: "Decomposed", score: 88, calls: 4 },
      { name: "ReAct", score: 84, calls: 5 },
      { name: "Socratic", score: 74, calls: 5 },
      { name: "Debate", score: 60, calls: 6 },
    ],
  },
  mmlu: {
    label: "MMLU",
    description: "Massive multitask knowledge",
    entries: [
      { name: "Chain of Thought", score: 82, calls: 1 },
      { name: "Self-Consistency", score: 80, calls: 5 },
      { name: "Recursive", score: 78, calls: 6 },
      { name: "Socratic", score: 76, calls: 5 },
      { name: "Tree of Thoughts", score: 74, calls: 7 },
      { name: "Debate", score: 72, calls: 6 },
      { name: "Standard", score: 66, calls: 1 },
      { name: "Self-Reflection", score: 60, calls: 3 },
      { name: "Refinement Loop", score: 60, calls: 8 },
      { name: "Decomposed", score: 54, calls: 4 },
      { name: "ReAct", score: 46, calls: 5 },
    ],
  },
  "arc-c": {
    label: "ARC-C",
    description: "Science challenge questions",
    entries: [
      { name: "Chain of Thought", score: 90, calls: 1 },
      { name: "Tree of Thoughts", score: 90, calls: 7 },
      { name: "Self-Consistency", score: 88, calls: 5 },
      { name: "Recursive", score: 88, calls: 6 },
      { name: "Debate", score: 86, calls: 6 },
      { name: "Self-Reflection", score: 86, calls: 3 },
      { name: "Socratic", score: 84, calls: 5 },
      { name: "Standard", score: 82, calls: 1 },
      { name: "Refinement Loop", score: 80, calls: 8 },
      { name: "ReAct", score: 70, calls: 5 },
      { name: "Decomposed", score: 60, calls: 4 },
    ],
  },
};

/* Consistent color per strategy name */
const STRATEGY_COLORS: Record<string, string> = {
  "Chain of Thought": "#f97316", // orange  (s1)
  "Tree of Thoughts": "#22d3ee", // cyan    (s2)
  "Self-Consistency": "#4ade80", // green   (s3)
  "Self-Reflection": "#86efac",  // light green (s3)
  "Recursive": "#a78bfa",       // purple  (s4)
  "Decomposed": "#f472b6",      // pink    (s5)
  "Refinement Loop": "#f9a8d4", // light pink (s5)
  "ReAct": "#67e8f9",           // light cyan (s2)
  "Socratic": "#fde047",        // light yellow (s6)
  "Standard": "#94a3b8",        // slate
  "Debate": "#2dd4bf",          // teal    (s7)
};

const DATASET_KEYS: DatasetKey[] = ["gsm8k", "mmlu", "arc-c"];

const MONO = "var(--font-mono), monospace";

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function StrategyComparisonWidget() {
  /* --- Hydration guard -------------------------------------------- */
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  /* --- State ------------------------------------------------------ */
  const [activeDataset, setActiveDataset] = useState<DatasetKey>("gsm8k");
  const [showCost, setShowCost] = useState(false);
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);
  const [animKey, setAnimKey] = useState(0); // bump to re-trigger bar animations

  /* --- Derived ---------------------------------------------------- */
  const dataset = DATASETS[activeDataset];

  const sorted = useMemo(() => {
    const entries = [...dataset.entries];
    if (showCost) {
      entries.sort((a, b) => b.calls - a.calls);
    } else {
      entries.sort((a, b) => b.score - a.score);
    }
    return entries;
  }, [dataset, showCost]);

  const maxValue = useMemo(() => {
    if (showCost) return Math.max(...sorted.map((e) => e.calls));
    return 100; // percentages cap at 100
  }, [sorted, showCost]);

  const avgScore = useMemo(() => {
    const sum = dataset.entries.reduce((s, e) => s + e.score, 0);
    return (sum / dataset.entries.length).toFixed(1);
  }, [dataset]);

  /* --- Handlers --------------------------------------------------- */
  const switchDataset = useCallback((key: DatasetKey) => {
    setActiveDataset(key);
    setAnimKey((k) => k + 1);
    setHoveredIdx(null);
  }, []);

  const toggleCost = useCallback(() => {
    setShowCost((v) => !v);
    setAnimKey((k) => k + 1);
    setHoveredIdx(null);
  }, []);

  /* ---------------------------------------------------------------- */
  /*  Render                                                           */
  /* ---------------------------------------------------------------- */

  if (!mounted) {
    return (
      <div className="widget-container s7">
        <div className="widget-label">Interactive &middot; Strategy Benchmarks</div>
        <div style={{ height: 360 }} />
      </div>
    );
  }

  return (
    <div className="widget-container s7">
      <div className="widget-label">Interactive &middot; Strategy Benchmarks</div>

      {/* ---- Dataset selector + Cost toggle ---- */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          gap: "0.5rem",
          marginBottom: "1.25rem",
        }}
      >
        {DATASET_KEYS.map((key) => (
          <button
            key={key}
            onClick={() => switchDataset(key)}
            className={`btn-mono ${key === activeDataset ? "active" : ""}`}
          >
            {DATASETS[key].label}
          </button>
        ))}

        <div style={{ flex: 1 }} />

        <button
          onClick={toggleCost}
          className={`btn-mono ${showCost ? "active" : ""}`}
          style={{
            borderColor: showCost ? "rgba(45,212,191,0.35)" : undefined,
            color: showCost ? "#2dd4bf" : undefined,
            background: showCost ? "rgba(45,212,191,0.1)" : undefined,
          }}
        >
          {showCost ? "LLM Calls" : "Accuracy"}
        </button>
      </div>

      {/* ---- Dataset description ---- */}
      <div
        style={{
          fontFamily: MONO,
          fontSize: "0.72rem",
          color: "#a1a1aa",
          marginBottom: "1rem",
          display: "flex",
          alignItems: "center",
          gap: "0.5rem",
        }}
      >
        <span
          style={{
            background: "rgba(45,212,191,0.12)",
            border: "1px solid rgba(45,212,191,0.25)",
            borderRadius: 4,
            padding: "0.15rem 0.45rem",
            color: "#2dd4bf",
            fontWeight: 600,
          }}
        >
          {dataset.label}
        </span>
        <span>{dataset.description}</span>
        <span style={{ marginLeft: "auto", color: "#71717a" }}>
          {showCost ? "Est. LLM calls / query" : "Accuracy %"}
        </span>
      </div>

      {/* ---- Bar chart ---- */}
      <div style={{ display: "flex", flexDirection: "column", gap: "0.35rem" }}>
        {sorted.map((entry, idx) => {
          const color = STRATEGY_COLORS[entry.name] ?? "#a1a1aa";
          const value = showCost ? entry.calls : entry.score;
          const pct = maxValue > 0 ? (value / maxValue) * 100 : 0;
          const isHovered = hoveredIdx === idx;
          const isTop = idx === 0;

          return (
            <div
              key={`${animKey}-${entry.name}`}
              onMouseEnter={() => setHoveredIdx(idx)}
              onMouseLeave={() => setHoveredIdx(null)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.65rem",
                padding: "0.15rem 0",
                cursor: "default",
                transition: "opacity 0.2s",
                opacity: hoveredIdx !== null && !isHovered ? 0.5 : 1,
              }}
            >
              {/* Strategy name */}
              <span
                style={{
                  fontFamily: MONO,
                  fontSize: "0.75rem",
                  color: isTop ? color : "#e4e4e7",
                  fontWeight: isTop ? 700 : 400,
                  minWidth: 130,
                  textAlign: "right",
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                }}
              >
                {entry.name}
              </span>

              {/* Bar track */}
              <div
                style={{
                  flex: 1,
                  height: 28,
                  background: "rgba(255,255,255,0.03)",
                  borderRadius: "0 6px 6px 0",
                  overflow: "hidden",
                  position: "relative",
                }}
              >
                {/* Animated bar */}
                <div
                  style={{
                    position: "absolute",
                    top: 0,
                    left: 0,
                    height: "100%",
                    width: `${pct}%`,
                    background: isHovered
                      ? color
                      : `linear-gradient(90deg, ${color}, ${color}88)`,
                    borderRadius: "0 6px 6px 0",
                    transition: "width 0.7s cubic-bezier(0.22, 1, 0.36, 1), background 0.2s",
                    animation: "barGrow 0.7s cubic-bezier(0.22, 1, 0.36, 1) both",
                    animationDelay: `${idx * 0.06}s`,
                    boxShadow: isHovered ? `0 0 14px ${color}40` : "none",
                  }}
                />

                {/* Hover tooltip */}
                {isHovered && (
                  <div
                    style={{
                      position: "absolute",
                      top: "50%",
                      left: `${Math.min(pct + 1, 85)}%`,
                      transform: "translateY(-50%)",
                      background: "#1a1b25",
                      border: "1px solid rgba(255,255,255,0.12)",
                      borderRadius: 6,
                      padding: "0.3rem 0.55rem",
                      fontFamily: MONO,
                      fontSize: "0.68rem",
                      color: "#e4e4e7",
                      whiteSpace: "nowrap",
                      zIndex: 10,
                      pointerEvents: "none",
                      boxShadow: "0 4px 12px rgba(0,0,0,0.5)",
                    }}
                  >
                    <span style={{ color }}>{entry.name}</span>
                    <span style={{ color: "#71717a" }}> &middot; </span>
                    <span>
                      {showCost
                        ? `${entry.calls} call${entry.calls !== 1 ? "s" : ""}`
                        : `${entry.score}%`}
                    </span>
                    <span style={{ color: "#71717a" }}> &middot; </span>
                    <span style={{ color: "#a1a1aa" }}>
                      {showCost
                        ? `Accuracy: ${entry.score}%`
                        : `${entry.calls} call${entry.calls !== 1 ? "s" : ""}/query`}
                    </span>
                  </div>
                )}
              </div>

              {/* Value label */}
              <span
                style={{
                  fontFamily: MONO,
                  fontSize: "0.78rem",
                  color: isTop ? color : "#e4e4e7",
                  fontWeight: isTop ? 700 : 500,
                  minWidth: 42,
                  textAlign: "right",
                }}
              >
                {showCost ? `${entry.calls}x` : `${entry.score}%`}
              </span>
            </div>
          );
        })}
      </div>

      {/* ---- Average score card ---- */}
      <div
        style={{
          marginTop: "1.25rem",
          display: "flex",
          alignItems: "center",
          gap: "0.85rem",
          background: "rgba(45,212,191,0.06)",
          border: "1px solid rgba(45,212,191,0.18)",
          borderRadius: 10,
          padding: "0.75rem 1rem",
        }}
      >
        {/* Icon */}
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
          <rect
            x="1"
            y="1"
            width="16"
            height="16"
            rx="3"
            stroke="#2dd4bf"
            strokeWidth="1.2"
            fill="rgba(45,212,191,0.1)"
          />
          <path
            d="M5 12V8M9 12V5M13 12V9"
            stroke="#2dd4bf"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
        </svg>

        <div style={{ display: "flex", flexDirection: "column", gap: "0.1rem" }}>
          <span
            style={{
              fontFamily: MONO,
              fontSize: "0.7rem",
              color: "#a1a1aa",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
            }}
          >
            Average accuracy on {dataset.label}
          </span>
          <div style={{ display: "flex", alignItems: "baseline", gap: "0.5rem" }}>
            <span
              style={{
                fontFamily: MONO,
                fontSize: "1.2rem",
                fontWeight: 700,
                color: "#2dd4bf",
              }}
            >
              {avgScore}%
            </span>
            <span
              style={{
                fontFamily: MONO,
                fontSize: "0.7rem",
                color: "#71717a",
              }}
            >
              across {dataset.entries.length} strategies
            </span>
          </div>
        </div>

        {/* Best strategy callout */}
        <div style={{ marginLeft: "auto", textAlign: "right" }}>
          <span
            style={{
              fontFamily: MONO,
              fontSize: "0.65rem",
              color: "#71717a",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
            }}
          >
            Best
          </span>
          <div
            style={{
              fontFamily: MONO,
              fontSize: "0.82rem",
              fontWeight: 600,
              color: STRATEGY_COLORS[sorted[0]?.name] ?? "#e4e4e7",
            }}
          >
            {sorted[0]?.name}
            <span style={{ color: "#a1a1aa", fontWeight: 400 }}>
              {" "}
              {showCost ? `${sorted[0]?.calls}x` : `${sorted[0]?.score}%`}
            </span>
          </div>
        </div>
      </div>

      {/* ---- Keyframe injection (inline, only once) ---- */}
      <style>{`
        @keyframes barGrow {
          from { width: 0%; }
        }
      `}</style>
    </div>
  );
}
