"use client";

import { useState, useCallback, useRef, useEffect } from "react";

/* ------------------------------------------------------------------ */
/*  Data                                                               */
/* ------------------------------------------------------------------ */

interface Strategy {
  key: string;
  label: string;
  color: string;
  description: string;
}

const STRATEGIES: Strategy[] = [
  { key: "standard",           label: "Standard",           color: "#a1a1aa", description: "Direct generation (baseline)" },
  { key: "cot",                label: "CoT",                color: "#22d3ee", description: "Chain-of-Thought reasoning" },
  { key: "tot",                label: "ToT",                color: "#4ade80", description: "Tree of Thoughts exploration" },
  { key: "react",              label: "ReAct",              color: "#f97316", description: "Reason + Act with tools" },
  { key: "reflection",         label: "Reflection",         color: "#a78bfa", description: "Draft \u2192 Critique \u2192 Refine" },
  { key: "consistency",        label: "Consistency",        color: "#f472b6", description: "Self-Consistency voting" },
  { key: "decomposed",         label: "Decomposed",         color: "#facc15", description: "Problem decomposition" },
  { key: "least_to_most",      label: "Least-to-Most",      color: "#2dd4bf", description: "Progressive subproblem solving" },
  { key: "recursive",          label: "Recursive",          color: "#fb923c", description: "Recursive LM (RLM)" },
  { key: "refinement",         label: "Refinement",         color: "#67e8f9", description: "Score-based iterative refinement" },
  { key: "complex_refinement", label: "Complex Refine",     color: "#c084fc", description: "5-stage optimization pipeline" },
  { key: "debate",             label: "Debate",             color: "#f43f5e", description: "Adversarial debate synthesis" },
  { key: "mcts",               label: "MCTS",               color: "#34d399", description: "Monte Carlo Tree Search" },
  { key: "analogical",         label: "Analogical",         color: "#fbbf24", description: "Reasoning by analogy" },
  { key: "socratic",           label: "Socratic",           color: "#818cf8", description: "Question-driven discovery" },
  { key: "meta",               label: "Meta",               color: "#e879f9", description: "Meta-cognitive orchestration" },
];

const EXAMPLES = [
  "gemma3:4b+cot",
  "llama3+react",
  "qwen3:9b+debate",
  "gemma3+meta",
];

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const MONO = "var(--font-mono), monospace";

function parseModelStrategy(input: string): { baseModel: string; strategy: string } {
  const trimmed = input.trim();
  const plusIdx = trimmed.lastIndexOf("+");
  if (plusIdx === -1 || plusIdx === 0 || plusIdx === trimmed.length - 1) {
    return { baseModel: trimmed || "...", strategy: "" };
  }
  return {
    baseModel: trimmed.slice(0, plusIdx),
    strategy: trimmed.slice(plusIdx + 1),
  };
}

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

/* ------------------------------------------------------------------ */
/*  Flow animation phases                                              */
/* ------------------------------------------------------------------ */

type FlowPhase =
  | "idle"
  | "to_interceptor"
  | "at_interceptor"
  | "to_agent"
  | "at_agent"
  | "to_ollama"
  | "at_ollama"
  | "to_response"
  | "done";

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function ArchitectureWidget() {
  /* --- Hydration guard -------------------------------------------- */
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  /* --- State ------------------------------------------------------ */
  const [input, setInput] = useState("gemma3:4b+cot");
  const [flowPhase, setFlowPhase] = useState<FlowPhase>("idle");
  const [flowColor, setFlowColor] = useState("#22d3ee");

  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  const parsed = parseModelStrategy(input);
  const matchedStrategy = STRATEGIES.find((s) => s.key === parsed.strategy);

  /* --- Timers cleanup -------------------------------------------- */
  const clearTimers = useCallback(() => {
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];
  }, []);

  useEffect(() => clearTimers, [clearTimers]);

  /* --- Start flow animation -------------------------------------- */
  const startFlow = useCallback(() => {
    clearTimers();
    const color = matchedStrategy?.color ?? "#a1a1aa";
    setFlowColor(color);
    setFlowPhase("idle");

    const phases: FlowPhase[] = [
      "to_interceptor",
      "at_interceptor",
      "to_agent",
      "at_agent",
      "to_ollama",
      "at_ollama",
      "to_response",
      "done",
    ];

    const delays = [100, 600, 1100, 1600, 2200, 2800, 3400, 4200];

    phases.forEach((phase, i) => {
      const t = setTimeout(() => setFlowPhase(phase), delays[i]);
      timersRef.current.push(t);
    });
  }, [matchedStrategy, clearTimers]);

  /* --- Example pill click ---------------------------------------- */
  const handleExample = useCallback(
    (example: string) => {
      setInput(example);
      clearTimers();
      setFlowPhase("idle");
    },
    [clearTimers],
  );

  /* --- Reset ----------------------------------------------------- */
  const reset = useCallback(() => {
    clearTimers();
    setFlowPhase("idle");
  }, [clearTimers]);

  /* --- SSR placeholder ------------------------------------------- */
  if (!mounted) {
    return (
      <div className="widget-container s7">
        <div className="widget-label">Interactive &middot; System Architecture</div>
        <div style={{ height: 400 }} />
      </div>
    );
  }

  /* --- Derived values -------------------------------------------- */
  const isFlowing = flowPhase !== "idle" && flowPhase !== "done";
  const isDone = flowPhase === "done";
  const hasMatch = !!matchedStrategy;

  /* ---------------------------------------------------------------- */
  /*  Render                                                           */
  /* ---------------------------------------------------------------- */

  return (
    <div className="widget-container s7">
      <div className="widget-label">Interactive &middot; System Architecture</div>

      {/* ---- Input Section ---- */}
      <div style={{ marginBottom: 24 }}>
        <div style={monoLabel("#a1a1aa", 8)}>Model + Strategy Input</div>
        <div
          style={{
            display: "flex",
            gap: 10,
            alignItems: "center",
            flexWrap: "wrap",
          }}
        >
          <input
            type="text"
            value={input}
            onChange={(e) => {
              setInput(e.target.value);
              if (flowPhase !== "idle") reset();
            }}
            placeholder='e.g. gemma3:4b+cot'
            style={{
              fontFamily: MONO,
              fontSize: "0.9rem",
              background: "rgba(0,0,0,0.4)",
              border: "1px solid rgba(255,255,255,0.12)",
              borderRadius: 8,
              padding: "8px 14px",
              color: "#e4e4e7",
              outline: "none",
              minWidth: 220,
              flex: 1,
              maxWidth: 320,
            }}
          />
          <button
            className="btn-mono"
            onClick={startFlow}
            disabled={isFlowing}
            style={{
              borderColor: isFlowing ? "rgba(255,255,255,0.04)" : "rgba(45,212,191,0.4)",
              color: isFlowing ? "#71717a" : "#2dd4bf",
              cursor: isFlowing ? "not-allowed" : "pointer",
            }}
          >
            {isFlowing ? "Routing..." : "Route Query"}
          </button>
          {(isFlowing || isDone) && (
            <button className="btn-mono" onClick={reset}>
              Reset
            </button>
          )}
        </div>

        {/* ---- Example Pills ---- */}
        <div style={{ display: "flex", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
          <span style={{ ...monoLabel("#71717a"), lineHeight: "28px", marginRight: 2 }}>
            Examples:
          </span>
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              onClick={() => handleExample(ex)}
              style={{
                fontFamily: MONO,
                fontSize: "0.72rem",
                padding: "4px 10px",
                borderRadius: 12,
                border: `1px solid ${input === ex ? "rgba(45,212,191,0.4)" : "rgba(255,255,255,0.08)"}`,
                background: input === ex ? "rgba(45,212,191,0.08)" : "transparent",
                color: input === ex ? "#2dd4bf" : "#a1a1aa",
                cursor: "pointer",
                transition: "all 0.15s",
              }}
            >
              {ex}
            </button>
          ))}
        </div>
      </div>

      {/* ---- Parse Result ---- */}
      <div
        className="code-block"
        style={{
          marginBottom: 24,
          display: "grid",
          gridTemplateColumns: "auto 1fr",
          gap: "4px 16px",
          alignItems: "baseline",
        }}
      >
        <span style={{ color: "#71717a" }}>input:</span>
        <span style={{ color: "#e4e4e7" }}>&quot;{input}&quot;</span>

        <span style={{ color: "#71717a" }}>base_model:</span>
        <span style={{ color: "#22d3ee" }}>&quot;{parsed.baseModel}&quot;</span>

        <span style={{ color: "#71717a" }}>strategy:</span>
        <span style={{ color: hasMatch ? matchedStrategy!.color : "#f43f5e" }}>
          &quot;{parsed.strategy || "none"}&quot;
          {parsed.strategy && !hasMatch && (
            <span style={{ color: "#f43f5e", marginLeft: 8, fontSize: "0.72rem" }}>
              (unknown strategy)
            </span>
          )}
        </span>

        <span style={{ color: "#71717a" }}>agent:</span>
        <span style={{ color: hasMatch ? matchedStrategy!.color : "#a1a1aa" }}>
          {hasMatch ? matchedStrategy!.label + "Agent" : "StandardAgent (fallback)"}
        </span>
      </div>

      {/* ---- Flow Diagram ---- */}
      <div style={monoLabel("#a1a1aa", 10)}>Data Flow</div>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 0,
          marginBottom: 28,
          overflowX: "auto",
          paddingBottom: 4,
        }}
      >
        <FlowBox
          label="User Query"
          sublabel="prompt text"
          borderColor="#a1a1aa"
          active={flowPhase === "idle" || flowPhase === "to_interceptor"}
          glow={flowPhase === "to_interceptor"}
          glowColor={flowColor}
        />
        <FlowArrow active={flowPhase === "to_interceptor"} color={flowColor} />

        <FlowBox
          label="Interceptor"
          sublabel="parse model+strategy"
          borderColor="#2dd4bf"
          active={
            flowPhase === "at_interceptor" ||
            flowPhase === "to_agent"
          }
          glow={flowPhase === "at_interceptor"}
          glowColor={flowColor}
        />
        <FlowArrow active={flowPhase === "to_agent"} color={flowColor} />

        <FlowBox
          label={hasMatch ? matchedStrategy!.label + "Agent" : "StandardAgent"}
          sublabel={hasMatch ? matchedStrategy!.description : "Direct generation"}
          borderColor={hasMatch ? matchedStrategy!.color : "#a1a1aa"}
          active={
            flowPhase === "at_agent" ||
            flowPhase === "to_ollama"
          }
          glow={flowPhase === "at_agent"}
          glowColor={flowColor}
        />
        <FlowArrow active={flowPhase === "to_ollama"} color={flowColor} />

        <FlowBox
          label="Ollama"
          sublabel="localhost:11434"
          borderColor="#71717a"
          active={
            flowPhase === "at_ollama" ||
            flowPhase === "to_response"
          }
          glow={flowPhase === "at_ollama"}
          glowColor={flowColor}
        />
        <FlowArrow active={flowPhase === "to_response"} color={flowColor} />

        <FlowBox
          label="Response"
          sublabel="streamed chunks"
          borderColor={isDone ? "#4ade80" : "#a1a1aa"}
          active={isDone}
          glow={isDone}
          glowColor="#4ade80"
        />
      </div>

      {/* ---- Animated Dot Bar ---- */}
      {isFlowing && (
        <div style={{ marginBottom: 24, position: "relative", height: 6 }}>
          <div
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              right: 0,
              height: 6,
              borderRadius: 3,
              background: "rgba(255,255,255,0.04)",
            }}
          />
          <div
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              height: 6,
              borderRadius: 3,
              background: flowColor,
              opacity: 0.6,
              transition: "width 0.5s ease-out",
              width: flowProgressWidth(flowPhase),
            }}
          />
          <div
            style={{
              position: "absolute",
              top: -3,
              width: 12,
              height: 12,
              borderRadius: "50%",
              background: flowColor,
              boxShadow: `0 0 12px ${flowColor}`,
              transition: "left 0.5s ease-out",
              left: flowDotLeft(flowPhase),
            }}
          />
        </div>
      )}

      {/* ---- Agent Map Grid ---- */}
      <div style={monoLabel("#a1a1aa", 10)}>Agent Map &mdash; 16 Strategies</div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: 8,
          marginBottom: 24,
        }}
      >
        {STRATEGIES.map((s) => {
          const isMatch = matchedStrategy?.key === s.key;
          const isActiveFlow = isMatch && (flowPhase === "at_agent" || flowPhase === "to_ollama");
          return (
            <div
              key={s.key}
              style={{
                background: isMatch
                  ? `rgba(${hexToRgb(s.color)}, 0.08)`
                  : "rgba(255,255,255,0.02)",
                border: `1px solid ${
                  isMatch ? s.color : "rgba(255,255,255,0.06)"
                }`,
                borderRadius: 8,
                padding: "8px 10px",
                transition: "all 0.3s",
                boxShadow: isActiveFlow
                  ? `0 0 16px rgba(${hexToRgb(s.color)}, 0.35), inset 0 0 12px rgba(${hexToRgb(s.color)}, 0.08)`
                  : isMatch
                  ? `0 0 8px rgba(${hexToRgb(s.color)}, 0.15)`
                  : "none",
                cursor: "default",
                position: "relative",
                overflow: "hidden",
              }}
            >
              {/* glow pulse behind active card */}
              {isActiveFlow && (
                <div
                  style={{
                    position: "absolute",
                    inset: 0,
                    background: `radial-gradient(circle at center, rgba(${hexToRgb(s.color)}, 0.12) 0%, transparent 70%)`,
                    animation: "pulse-glow-card 1.5s ease-in-out infinite",
                  }}
                />
              )}
              <div
                style={{
                  fontFamily: MONO,
                  fontSize: "0.72rem",
                  fontWeight: 600,
                  color: isMatch ? s.color : "#a1a1aa",
                  marginBottom: 2,
                  position: "relative",
                }}
              >
                {s.label}
              </div>
              <div
                style={{
                  fontSize: "0.65rem",
                  color: isMatch ? "rgba(255,255,255,0.6)" : "#52525b",
                  lineHeight: 1.3,
                  position: "relative",
                }}
              >
                {s.description}
              </div>
            </div>
          );
        })}
      </div>

      {/* ---- Ollama Connection ---- */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          padding: "10px 14px",
          background: "rgba(0,0,0,0.3)",
          border: "1px solid rgba(255,255,255,0.06)",
          borderRadius: 8,
          marginBottom: 16,
        }}
      >
        <div
          style={{
            width: 8,
            height: 8,
            borderRadius: "50%",
            background:
              flowPhase === "at_ollama" || flowPhase === "to_response"
                ? "#4ade80"
                : "#71717a",
            boxShadow:
              flowPhase === "at_ollama" || flowPhase === "to_response"
                ? "0 0 8px rgba(74,222,128,0.5)"
                : "none",
            transition: "all 0.3s",
          }}
        />
        <span
          style={{
            fontFamily: MONO,
            fontSize: "0.75rem",
            color: "#a1a1aa",
          }}
        >
          Ollama &middot; http://localhost:11434
        </span>
        <span
          style={{
            fontFamily: MONO,
            fontSize: "0.65rem",
            color: "#52525b",
            marginLeft: "auto",
          }}
        >
          {flowPhase === "at_ollama"
            ? "Generating..."
            : flowPhase === "to_response" || isDone
            ? "Streaming response"
            : "Waiting for request"}
        </span>
      </div>

      {/* ---- Architecture Labels ---- */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: 12,
        }}
      >
        <ArchLabel
          title="ReasoningInterceptor"
          desc="Drop-in Ollama replacement. Parses model+strategy naming convention and routes to the correct agent."
          color="#2dd4bf"
        />
        <ArchLabel
          title="AGENT_MAP"
          desc="Registry mapping strategy keys to agent classes. Single source of truth for all 16 reasoning strategies."
          color="#a78bfa"
        />
        <ArchLabel
          title="BaseAgent"
          desc="Abstract base class providing OllamaClient connection, streaming interface, and colored logging."
          color="#f97316"
        />
        <ArchLabel
          title="OllamaClient"
          desc="HTTP wrapper for Ollama API. Handles streaming and non-streaming responses with configurable parameters."
          color="#71717a"
        />
      </div>

      {/* Keyframes injected via style tag for card pulse */}
      <style>{`
        @keyframes pulse-glow-card {
          0%, 100% { opacity: 0.5; }
          50% { opacity: 1; }
        }
      `}</style>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Sub-Components                                                     */
/* ------------------------------------------------------------------ */

function FlowBox({
  label,
  sublabel,
  borderColor,
  active,
  glow,
  glowColor,
}: {
  label: string;
  sublabel: string;
  borderColor: string;
  active: boolean;
  glow: boolean;
  glowColor: string;
}) {
  return (
    <div
      style={{
        minWidth: 110,
        padding: "10px 14px",
        background: active
          ? `rgba(${hexToRgb(borderColor)}, 0.06)`
          : "rgba(255,255,255,0.02)",
        border: `1px solid ${active ? borderColor : "rgba(255,255,255,0.08)"}`,
        borderRadius: 8,
        textAlign: "center",
        transition: "all 0.35s",
        boxShadow: glow
          ? `0 0 14px rgba(${hexToRgb(glowColor)}, 0.3)`
          : "none",
        flexShrink: 0,
      }}
    >
      <div
        style={{
          fontFamily: MONO,
          fontSize: "0.75rem",
          fontWeight: 600,
          color: active ? borderColor : "#a1a1aa",
          marginBottom: 2,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: "0.65rem",
          color: active ? "rgba(255,255,255,0.5)" : "#52525b",
        }}
      >
        {sublabel}
      </div>
    </div>
  );
}

function FlowArrow({ active, color }: { active: boolean; color: string }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        padding: "0 2px",
        flexShrink: 0,
      }}
    >
      <svg width="32" height="16" viewBox="0 0 32 16">
        <line
          x1="0"
          y1="8"
          x2="24"
          y2="8"
          stroke={active ? color : "rgba(255,255,255,0.1)"}
          strokeWidth="2"
          style={{ transition: "stroke 0.3s" }}
        />
        <polygon
          points="24,3 32,8 24,13"
          fill={active ? color : "rgba(255,255,255,0.1)"}
          style={{ transition: "fill 0.3s" }}
        />
        {active && (
          <circle r="3" fill={color} opacity="0.9">
            <animateMotion dur="0.5s" repeatCount="indefinite" path="M0,8 L24,8" />
          </circle>
        )}
      </svg>
    </div>
  );
}

function ArchLabel({
  title,
  desc,
  color,
}: {
  title: string;
  desc: string;
  color: string;
}) {
  return (
    <div
      style={{
        padding: "10px 14px",
        background: "rgba(0,0,0,0.2)",
        borderLeft: `2px solid ${color}`,
        borderRadius: "0 6px 6px 0",
      }}
    >
      <div
        style={{
          fontFamily: MONO,
          fontSize: "0.7rem",
          fontWeight: 600,
          color,
          marginBottom: 4,
          textTransform: "uppercase",
          letterSpacing: "0.06em",
        }}
      >
        {title}
      </div>
      <div style={{ fontSize: "0.72rem", color: "#a1a1aa", lineHeight: 1.5 }}>
        {desc}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Utilities                                                          */
/* ------------------------------------------------------------------ */

function hexToRgb(hex: string): string {
  const h = hex.replace("#", "");
  const bigint = parseInt(h, 16);
  const r = (bigint >> 16) & 255;
  const g = (bigint >> 8) & 255;
  const b = bigint & 255;
  return `${r},${g},${b}`;
}

function flowProgressWidth(phase: FlowPhase): string {
  switch (phase) {
    case "to_interceptor":
      return "10%";
    case "at_interceptor":
      return "25%";
    case "to_agent":
      return "40%";
    case "at_agent":
      return "55%";
    case "to_ollama":
      return "70%";
    case "at_ollama":
      return "85%";
    case "to_response":
      return "95%";
    case "done":
      return "100%";
    default:
      return "0%";
  }
}

function flowDotLeft(phase: FlowPhase): string {
  switch (phase) {
    case "to_interceptor":
      return "8%";
    case "at_interceptor":
      return "23%";
    case "to_agent":
      return "38%";
    case "at_agent":
      return "53%";
    case "to_ollama":
      return "68%";
    case "at_ollama":
      return "83%";
    case "to_response":
      return "93%";
    case "done":
      return "98%";
    default:
      return "0%";
  }
}
