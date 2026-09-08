"use client";

import { useState, useCallback, useRef, useEffect } from "react";

/* ------------------------------------------------------------------ */
/*  Data                                                               */
/* ------------------------------------------------------------------ */

interface Route {
  category: string;
  strategy: string;
  description: string;
}

interface ExampleQuery {
  text: string;
  category: string;
  confidence: number;
}

const ROUTING_TABLE: Route[] = [
  { category: "math", strategy: "Chain of Thought", description: "Breaks the problem into sequential arithmetic or algebraic steps, verifying each before proceeding to the next." },
  { category: "logic", strategy: "Tree of Thoughts", description: "Explores multiple reasoning branches in parallel, scoring and pruning paths to find the most logically sound conclusion." },
  { category: "creative", strategy: "Self-Reflection", description: "Generates an initial draft, then critiques and refines it across multiple iterations for originality and coherence." },
  { category: "factual", strategy: "ReAct", description: "Interleaves reasoning with tool-use actions (search, lookup) to ground answers in retrieved evidence." },
  { category: "controversial", strategy: "Debate", description: "Stages a structured PRO vs CON debate with a judge, synthesizing a balanced verdict from competing arguments." },
  { category: "planning", strategy: "Decomposed", description: "Splits a complex goal into ordered sub-tasks, solves each independently, then assembles the results into a unified plan." },
  { category: "philosophical", strategy: "Socratic", description: "Asks progressively deeper clarifying questions, guiding the user toward insight rather than delivering a flat answer." },
];

const EXAMPLE_QUERIES: ExampleQuery[] = [
  { text: "What is 15% of 340?", category: "math", confidence: 96 },
  { text: "Write a poem about rain", category: "creative", confidence: 91 },
  { text: "Is nuclear energy safe?", category: "controversial", confidence: 88 },
  { text: "Plan a road trip from LA to NYC", category: "planning", confidence: 93 },
  { text: "What year did the Titanic sink?", category: "factual", confidence: 97 },
];

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const MONO = "var(--font-mono), monospace";
const TEAL = "#2dd4bf";
const TEAL_DIM = "rgba(45,212,191,0.15)";
const TEAL_GLOW = "rgba(45,212,191,0.25)";

function monoLabel(color: string, mb?: number): React.CSSProperties {
  return {
    fontFamily: MONO,
    fontSize: "0.7rem",
    textTransform: "uppercase",
    letterSpacing: "0.08em",
    color,
    fontWeight: 600,
    marginBottom: mb ?? 0,
  };
}

function classifyQuery(query: string): { category: string; confidence: number } | null {
  const q = query.toLowerCase().trim();
  if (!q) return null;

  // Check against examples first (exact match)
  const exact = EXAMPLE_QUERIES.find((e) => e.text.toLowerCase() === q);
  if (exact) return { category: exact.category, confidence: exact.confidence };

  // Keyword heuristics
  const patterns: { category: string; keywords: RegExp; confidence: number }[] = [
    { category: "math", keywords: /\b(\d+\s*[%+\-*/x]\s*\d+|percent|calculate|how\s+much|sum|total|divide|multiply|average|equation)\b/i, confidence: 94 },
    { category: "factual", keywords: /\b(what\s+(year|day|is|was|are|were)|who\s+(is|was|invented|discovered)|when\s+did|where\s+(is|was)|how\s+many|capital\s+of|population)\b/i, confidence: 92 },
    { category: "creative", keywords: /\b(write|poem|story|song|compose|haiku|limerick|creative|imagine|fiction|narrative)\b/i, confidence: 89 },
    { category: "planning", keywords: /\b(plan|schedule|itinerary|organize|road\s+trip|steps\s+to|how\s+to\s+build|project|roadmap|strategy\s+for)\b/i, confidence: 90 },
    { category: "controversial", keywords: /\b(safe|ethical|should\s+we|pros?\s+and\s+cons?|debate|controversial|moral|opinion\s+on|is\s+it\s+right)\b/i, confidence: 85 },
    { category: "philosophical", keywords: /\b(meaning\s+of|consciousness|free\s+will|exist|purpose|why\s+do\s+we|nature\s+of|what\s+is\s+truth|reality)\b/i, confidence: 87 },
    { category: "logic", keywords: /\b(puzzle|riddle|paradox|syllogism|if\s+then|logical|deduce|infer|contradict|prove)\b/i, confidence: 91 },
  ];

  for (const p of patterns) {
    if (p.keywords.test(q)) {
      // Add slight randomness to confidence so it feels dynamic
      const jitter = Math.floor(Math.random() * 5) - 2;
      return { category: p.category, confidence: Math.min(99, Math.max(70, p.confidence + jitter)) };
    }
  }

  // Fallback: pick a plausible default
  return { category: "factual", confidence: 72 };
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function MetaReasoningWidget() {
  /* --- Hydration guard -------------------------------------------- */
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  /* --- State ------------------------------------------------------ */
  const [query, setQuery] = useState("");
  const [phase, setPhase] = useState<"idle" | "analyzing" | "categorized" | "routed" | "done">("idle");
  const [analysisStep, setAnalysisStep] = useState(0); // 0=none, 1=analyzing, 2=categorized, 3=routed
  const [result, setResult] = useState<{ category: string; confidence: number; strategy: string; description: string } | null>(null);

  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  /* --- Timers cleanup -------------------------------------------- */
  const clearTimers = useCallback(() => {
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];
  }, []);

  useEffect(() => clearTimers, [clearTimers]);

  /* --- Reset ----------------------------------------------------- */
  const reset = useCallback(() => {
    clearTimers();
    setPhase("idle");
    setAnalysisStep(0);
    setResult(null);
  }, [clearTimers]);

  /* --- Classify -------------------------------------------------- */
  const runClassification = useCallback(
    (q?: string) => {
      const input = q ?? query;
      if (!input.trim()) return;

      reset();
      setPhase("analyzing");
      setAnalysisStep(1);

      // Step 1: Analyzing (spin for 800ms)
      const t1 = setTimeout(() => {
        const classification = classifyQuery(input);
        if (!classification) return;

        const route = ROUTING_TABLE.find((r) => r.category === classification.category);
        if (!route) return;

        setResult({
          category: classification.category,
          confidence: classification.confidence,
          strategy: route.strategy,
          description: route.description,
        });

        setPhase("categorized");
        setAnalysisStep(2);
      }, 800);
      timersRef.current.push(t1);

      // Step 2: Show route after another 600ms
      const t2 = setTimeout(() => {
        setPhase("routed");
        setAnalysisStep(3);
      }, 1400);
      timersRef.current.push(t2);

      // Step 3: Final done state
      const t3 = setTimeout(() => {
        setPhase("done");
      }, 1800);
      timersRef.current.push(t3);
    },
    [query, reset],
  );

  /* --- Example click --------------------------------------------- */
  const handleExample = useCallback(
    (example: ExampleQuery) => {
      setQuery(example.text);
      // Small delay so user sees the text appear before classification starts
      const t = setTimeout(() => {
        runClassification(example.text);
      }, 150);
      timersRef.current.push(t);
    },
    [runClassification],
  );

  /* --- Key handler ----------------------------------------------- */
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && query.trim()) {
        runClassification();
      }
    },
    [query, runClassification],
  );

  /* --- Confidence bar color -------------------------------------- */
  const confidenceColor = (conf: number): string => {
    if (conf >= 90) return TEAL;
    if (conf >= 80) return "#5eead4";
    if (conf >= 70) return "#99f6e4";
    return "#a1a1aa";
  };

  /* ---------------------------------------------------------------- */
  /*  Render                                                           */
  /* ---------------------------------------------------------------- */

  return (
    <div className="widget-container s7">
      <div className="widget-label">Interactive &middot; Meta-Reasoning Router</div>

      {/* ---- Input area ---- */}
      <div
        style={{
          display: "flex",
          gap: "0.5rem",
          marginBottom: "0.75rem",
        }}
      >
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a query to classify..."
          style={{
            flex: 1,
            background: "transparent",
            border: "1px solid rgba(255,255,255,0.12)",
            borderRadius: 6,
            padding: "0.55rem 0.75rem",
            color: "#e4e4e7",
            fontFamily: MONO,
            fontSize: "0.84rem",
            outline: "none",
            transition: "border-color 0.2s",
          }}
          onFocus={(e) => {
            e.currentTarget.style.borderColor = "rgba(45,212,191,0.4)";
          }}
          onBlur={(e) => {
            e.currentTarget.style.borderColor = "rgba(255,255,255,0.12)";
          }}
        />
        <button
          className="btn-mono"
          onClick={() => runClassification()}
          disabled={!query.trim() || phase === "analyzing"}
          style={{
            background: !query.trim() || phase === "analyzing" ? "transparent" : TEAL_DIM,
            borderColor: !query.trim() || phase === "analyzing" ? "rgba(255,255,255,0.08)" : "rgba(45,212,191,0.35)",
            color: !query.trim() || phase === "analyzing" ? "#a1a1aa" : TEAL,
            cursor: !query.trim() || phase === "analyzing" ? "not-allowed" : "pointer",
            paddingLeft: "1rem",
            paddingRight: "1rem",
          }}
        >
          {phase === "analyzing" ? "Classifying\u2026" : "Classify"}
        </button>
        {phase !== "idle" && (
          <button className="btn-mono" onClick={() => { reset(); setQuery(""); }}>
            Reset
          </button>
        )}
      </div>

      {/* ---- Example pills ---- */}
      <div className="flex flex-wrap gap-2 mb-5">
        {EXAMPLE_QUERIES.map((ex) => (
          <button
            key={ex.text}
            className="btn-mono"
            onClick={() => handleExample(ex)}
            style={{
              fontSize: "0.72rem",
              padding: "0.25rem 0.6rem",
            }}
          >
            {ex.text}
          </button>
        ))}
      </div>

      {/* ---- Analysis steps ---- */}
      {phase !== "idle" && (
        <div
          className="animate-fade-in"
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "0.6rem",
            marginBottom: "1.25rem",
          }}
        >
          {/* Step 1: Analyzing */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.6rem",
              opacity: analysisStep >= 1 ? 1 : 0.3,
              transition: "opacity 0.3s",
            }}
          >
            {analysisStep === 1 && phase === "analyzing" ? (
              mounted && (
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 16 16"
                  style={{ animation: "spin 1s linear infinite", flexShrink: 0 }}
                >
                  <circle cx="8" cy="8" r="6" stroke="rgba(45,212,191,0.3)" strokeWidth="2" fill="none" />
                  <path d="M8 2 A6 6 0 0 1 14 8" stroke={TEAL} strokeWidth="2" fill="none" strokeLinecap="round" />
                </svg>
              )
            ) : analysisStep >= 2 ? (
              mounted && (
                <svg width="16" height="16" viewBox="0 0 16 16" style={{ flexShrink: 0 }}>
                  <circle cx="8" cy="8" r="6" stroke={TEAL} strokeWidth="1.5" fill="rgba(45,212,191,0.1)" />
                  <path d="M5 8 L7 10 L11 6" stroke={TEAL} strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              )
            ) : (
              <div style={{ width: 16, height: 16, flexShrink: 0 }} />
            )}
            <span style={{ fontFamily: MONO, fontSize: "0.78rem", color: analysisStep >= 2 ? TEAL : "#a1a1aa" }}>
              Query analyzed
            </span>
          </div>

          {/* Step 2: Category determined */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.6rem",
              opacity: analysisStep >= 2 ? 1 : 0.3,
              transition: "opacity 0.3s",
            }}
          >
            {analysisStep === 2 && phase === "categorized" ? (
              mounted && (
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 16 16"
                  style={{ animation: "spin 1s linear infinite", flexShrink: 0 }}
                >
                  <circle cx="8" cy="8" r="6" stroke="rgba(45,212,191,0.3)" strokeWidth="2" fill="none" />
                  <path d="M8 2 A6 6 0 0 1 14 8" stroke={TEAL} strokeWidth="2" fill="none" strokeLinecap="round" />
                </svg>
              )
            ) : analysisStep >= 3 ? (
              mounted && (
                <svg width="16" height="16" viewBox="0 0 16 16" style={{ flexShrink: 0 }}>
                  <circle cx="8" cy="8" r="6" stroke={TEAL} strokeWidth="1.5" fill="rgba(45,212,191,0.1)" />
                  <path d="M5 8 L7 10 L11 6" stroke={TEAL} strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              )
            ) : (
              <div style={{ width: 16, height: 16, flexShrink: 0 }} />
            )}
            <span style={{ fontFamily: MONO, fontSize: "0.78rem", color: analysisStep >= 3 ? TEAL : "#a1a1aa" }}>
              Category: {result ? result.category : "\u2026"}
              {result && (
                <span style={{ color: "#a1a1aa", marginLeft: "0.5rem" }}>
                  ({result.confidence}% confidence)
                </span>
              )}
            </span>
          </div>

          {/* Step 3: Strategy selected */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.6rem",
              opacity: analysisStep >= 3 ? 1 : 0.3,
              transition: "opacity 0.3s",
            }}
          >
            {analysisStep >= 3 && phase === "done" ? (
              mounted && (
                <svg width="16" height="16" viewBox="0 0 16 16" style={{ flexShrink: 0 }}>
                  <circle cx="8" cy="8" r="6" stroke={TEAL} strokeWidth="1.5" fill="rgba(45,212,191,0.1)" />
                  <path d="M5 8 L7 10 L11 6" stroke={TEAL} strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              )
            ) : analysisStep >= 3 && phase === "routed" ? (
              mounted && (
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 16 16"
                  style={{ animation: "spin 1s linear infinite", flexShrink: 0 }}
                >
                  <circle cx="8" cy="8" r="6" stroke="rgba(45,212,191,0.3)" strokeWidth="2" fill="none" />
                  <path d="M8 2 A6 6 0 0 1 14 8" stroke={TEAL} strokeWidth="2" fill="none" strokeLinecap="round" />
                </svg>
              )
            ) : (
              <div style={{ width: 16, height: 16, flexShrink: 0 }} />
            )}
            <span style={{ fontFamily: MONO, fontSize: "0.78rem", color: phase === "done" ? TEAL : "#a1a1aa" }}>
              Strategy: {result ? result.strategy : "\u2026"}
            </span>
          </div>
        </div>
      )}

      {/* ---- Confidence meter ---- */}
      {result && analysisStep >= 2 && (
        <div className="animate-fade-in" style={{ marginBottom: "1.25rem" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.35rem" }}>
            <span style={monoLabel("#a1a1aa")}>Confidence</span>
            <span
              style={{
                fontFamily: MONO,
                fontSize: "0.85rem",
                fontWeight: 700,
                color: confidenceColor(result.confidence),
              }}
            >
              {result.confidence}%
            </span>
          </div>
          <div
            style={{
              height: 8,
              borderRadius: 4,
              background: "rgba(255,255,255,0.06)",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                width: `${result.confidence}%`,
                height: "100%",
                borderRadius: 4,
                background: `linear-gradient(90deg, rgba(45,212,191,0.4), ${TEAL})`,
                transition: "width 0.6s ease-out",
                boxShadow: `0 0 12px rgba(45,212,191,0.3)`,
              }}
            />
          </div>
        </div>
      )}

      {/* ---- Routing table ---- */}
      <div style={{ marginBottom: "1.25rem" }}>
        <span style={{ ...monoLabel("#a1a1aa"), display: "block", marginBottom: "0.55rem" }}>
          Routing Table
        </span>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 0,
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: 8,
            overflow: "hidden",
          }}
        >
          {/* Header */}
          <div
            style={{
              padding: "0.45rem 0.75rem",
              background: "rgba(255,255,255,0.04)",
              borderBottom: "1px solid rgba(255,255,255,0.08)",
              borderRight: "1px solid rgba(255,255,255,0.08)",
            }}
          >
            <span style={monoLabel("#a1a1aa")}>Category</span>
          </div>
          <div
            style={{
              padding: "0.45rem 0.75rem",
              background: "rgba(255,255,255,0.04)",
              borderBottom: "1px solid rgba(255,255,255,0.08)",
            }}
          >
            <span style={monoLabel("#a1a1aa")}>Strategy</span>
          </div>

          {/* Rows */}
          {ROUTING_TABLE.map((route, idx) => {
            const isActive = result?.category === route.category && phase === "done";
            const isLast = idx === ROUTING_TABLE.length - 1;
            return (
              <div key={route.category} style={{ display: "contents" }}>
                <div
                  style={{
                    padding: "0.45rem 0.75rem",
                    background: isActive ? TEAL_DIM : "transparent",
                    borderBottom: isLast ? "none" : "1px solid rgba(255,255,255,0.06)",
                    borderRight: "1px solid rgba(255,255,255,0.08)",
                    transition: "background 0.3s, box-shadow 0.3s",
                    boxShadow: isActive ? `inset 0 0 20px ${TEAL_GLOW}` : "none",
                    display: "flex",
                    alignItems: "center",
                    gap: "0.4rem",
                  }}
                >
                  {isActive && mounted && (
                    <svg width="10" height="10" viewBox="0 0 10 10" style={{ flexShrink: 0 }}>
                      <circle cx="5" cy="5" r="4" fill={TEAL} style={{ animation: "pulseGlow 2s ease-in-out infinite" }} />
                    </svg>
                  )}
                  <span
                    style={{
                      fontFamily: MONO,
                      fontSize: "0.78rem",
                      color: isActive ? TEAL : "#e4e4e7",
                      fontWeight: isActive ? 700 : 400,
                    }}
                  >
                    {route.category}
                  </span>
                </div>
                <div
                  style={{
                    padding: "0.45rem 0.75rem",
                    background: isActive ? TEAL_DIM : "transparent",
                    borderBottom: isLast ? "none" : "1px solid rgba(255,255,255,0.06)",
                    transition: "background 0.3s, box-shadow 0.3s",
                    boxShadow: isActive ? `inset 0 0 20px ${TEAL_GLOW}` : "none",
                  }}
                >
                  <span
                    style={{
                      fontFamily: MONO,
                      fontSize: "0.78rem",
                      color: isActive ? TEAL : "#a1a1aa",
                      fontWeight: isActive ? 700 : 400,
                    }}
                  >
                    {route.strategy}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ---- Selected strategy card ---- */}
      {result && phase === "done" && (
        <div
          className="animate-fade-in"
          style={{
            background: TEAL_DIM,
            border: `1px solid rgba(45,212,191,0.3)`,
            borderLeftWidth: 3,
            borderLeftColor: TEAL,
            borderRadius: 8,
            padding: "0.85rem 1rem",
            boxShadow: `0 0 24px rgba(45,212,191,0.08)`,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.4rem" }}>
            {mounted && (
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path
                  d="M8 1 L10 5.5 L15 6 L11.5 9.5 L12.5 14.5 L8 12 L3.5 14.5 L4.5 9.5 L1 6 L6 5.5 Z"
                  stroke={TEAL}
                  strokeWidth="1"
                  fill="rgba(45,212,191,0.15)"
                  strokeLinejoin="round"
                />
              </svg>
            )}
            <span
              style={{
                fontFamily: MONO,
                fontSize: "0.72rem",
                color: TEAL,
                fontWeight: 700,
                textTransform: "uppercase",
                letterSpacing: "0.08em",
              }}
            >
              Selected Strategy
            </span>
          </div>
          <p
            style={{
              fontFamily: MONO,
              fontSize: "0.95rem",
              fontWeight: 700,
              color: "#e4e4e7",
              margin: "0 0 0.35rem",
            }}
          >
            {result.strategy}
          </p>
          <p
            style={{
              color: "#b4b4bc",
              margin: 0,
              fontSize: "0.82rem",
              lineHeight: 1.7,
            }}
          >
            {result.description}
          </p>
        </div>
      )}

      {/* ---- Idle placeholder ---- */}
      {phase === "idle" && (
        <div
          className="rounded-lg flex items-center justify-center"
          style={{
            height: 80,
            border: "1px dashed rgba(255,255,255,0.1)",
            color: "#a1a1aa",
            fontFamily: MONO,
            fontSize: "0.78rem",
            marginTop: "0.25rem",
          }}
        >
          Type a query or pick an example to classify
        </div>
      )}

      {/* ---- Inline keyframes for spinner ---- */}
      {mounted && (
        <style>{`
          @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
          }
        `}</style>
      )}
    </div>
  );
}
