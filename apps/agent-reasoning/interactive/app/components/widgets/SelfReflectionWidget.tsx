"use client";

import { useState, useCallback, useRef, useEffect } from "react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface Phase {
  type: "draft" | "critique" | "improvement";
  text: string;
}

interface Iteration {
  number: number;
  phases: Phase[];
  status: "pending" | "needs_improvement" | "correct";
  critique: string;
}

interface Prompt {
  label: string;
  iterations: Iteration[];
}

/* ------------------------------------------------------------------ */
/*  Static data - all prompts and their pre-baked iterations           */
/* ------------------------------------------------------------------ */

const PROMPTS: Prompt[] = [
  {
    label: "Write a haiku about artificial intelligence",
    iterations: [
      {
        number: 1,
        phases: [
          {
            type: "draft",
            text: "Silicon minds think\nProcessing data streams\nAnswers emerge now",
          },
          {
            type: "critique",
            text: 'The haiku follows 5-7-5 syllable structure but lacks emotional depth. The imagery is too technical and reads like a product description rather than poetry. "Answers emerge now" feels flat.',
          },
        ],
        status: "needs_improvement",
        critique:
          'The haiku follows 5-7-5 syllable structure but lacks emotional depth. The imagery is too technical and reads like a product description rather than poetry. "Answers emerge now" feels flat.',
      },
      {
        number: 2,
        phases: [
          {
            type: "improvement",
            text: "Dreams in binary\nLearning what it means to know\nAlmost human, yet",
          },
          {
            type: "critique",
            text: "Much better emotional resonance. The juxtaposition of dreaming and binary creates tension. The last line creates philosophical weight and ambiguity. CORRECT.",
          },
        ],
        status: "correct",
        critique:
          "Much better emotional resonance. The juxtaposition of dreaming and binary creates tension. The last line creates philosophical weight and ambiguity. CORRECT.",
      },
    ],
  },
  {
    label: "Explain recursion in one sentence",
    iterations: [
      {
        number: 1,
        phases: [
          {
            type: "draft",
            text: "Recursion is when a function calls itself repeatedly until a base condition is met.",
          },
          {
            type: "critique",
            text: "Technically accurate but reads like a textbook definition. Misses the elegance of the concept. Could be more memorable and illustrative.",
          },
        ],
        status: "needs_improvement",
        critique:
          "Technically accurate but reads like a textbook definition. Misses the elegance of the concept. Could be more memorable and illustrative.",
      },
      {
        number: 2,
        phases: [
          {
            type: "improvement",
            text: "Recursion is the art of solving a problem by asking a slightly simpler version of yourself the same question, all the way down until the answer is obvious.",
          },
          {
            type: "critique",
            text: "Excellent\u2014captures both the mechanism (self-referencing with simplification) and the intuition (asking yourself). The phrase 'all the way down' evokes turtles-all-the-way-down. CORRECT.",
          },
        ],
        status: "correct",
        critique:
          "Excellent\u2014captures both the mechanism (self-referencing with simplification) and the intuition (asking yourself). The phrase 'all the way down' evokes turtles-all-the-way-down. CORRECT.",
      },
    ],
  },
  {
    label: "Write a metaphor for how neural networks learn",
    iterations: [
      {
        number: 1,
        phases: [
          {
            type: "draft",
            text: "A neural network is like a student studying for an exam by reviewing many practice tests.",
          },
          {
            type: "critique",
            text: "The metaphor is understandable but superficial. It doesn't capture the distributed nature of learning or the way weights adjust. Too generic\u2014could describe any learning system.",
          },
        ],
        status: "needs_improvement",
        critique:
          "The metaphor is understandable but superficial. It doesn't capture the distributed nature of learning or the way weights adjust. Too generic\u2014could describe any learning system.",
      },
      {
        number: 2,
        phases: [
          {
            type: "improvement",
            text: "A neural network learns the way a river carves a canyon: each example flows through, deepening the channels that lead to correct answers and slowly eroding the paths that lead astray, until the landscape of its understanding mirrors the shape of the data.",
          },
          {
            type: "critique",
            text: "Striking improvement. The erosion metaphor captures gradient descent intuitively. 'Landscape of understanding' mirrors the loss-landscape concept. Rich but not overwrought. Minor: slightly long. CORRECT.",
          },
        ],
        status: "correct",
        critique:
          "Striking improvement. The erosion metaphor captures gradient descent intuitively. 'Landscape of understanding' mirrors the loss-landscape concept. Rich but not overwrought. Minor: slightly long. CORRECT.",
      },
    ],
  },
];

const MAX_TURNS = 5;

/* ------------------------------------------------------------------ */
/*  Tiny helpers                                                       */
/* ------------------------------------------------------------------ */

function phaseBadgeColor(type: Phase["type"]): {
  bg: string;
  text: string;
  label: string;
} {
  switch (type) {
    case "draft":
      return { bg: "rgba(59,130,246,0.15)", text: "#60a5fa", label: "DRAFT" };
    case "critique":
      return {
        bg: "rgba(249,115,22,0.15)",
        text: "#fb923c",
        label: "CRITIQUE",
      };
    case "improvement":
      return {
        bg: "rgba(74,222,128,0.15)",
        text: "#4ade80",
        label: "IMPROVEMENT",
      };
  }
}

function statusBadge(status: Iteration["status"]) {
  if (status === "correct") {
    return {
      bg: "rgba(74,222,128,0.12)",
      border: "rgba(74,222,128,0.3)",
      text: "#4ade80",
      label: "CORRECT",
    };
  }
  if (status === "needs_improvement") {
    return {
      bg: "rgba(239,68,68,0.12)",
      border: "rgba(239,68,68,0.3)",
      text: "#f87171",
      label: "NEEDS IMPROVEMENT",
    };
  }
  return {
    bg: "transparent",
    border: "rgba(255,255,255,0.08)",
    text: "#a1a1aa",
    label: "PENDING",
  };
}

/** Simple word-level diff: returns tokens with a `changed` flag. */
function wordDiff(
  before: string,
  after: string
): { word: string; changed: boolean }[] {
  const wordsA = before.split(/\s+/);
  const wordsB = after.split(/\s+/);
  return wordsB.map((w, i) => ({
    word: w,
    changed: wordsA[i] !== w,
  }));
}

/* ------------------------------------------------------------------ */
/*  Sub-components                                                     */
/* ------------------------------------------------------------------ */

/** Circular flow diagram: Draft -> Critique -> Improve */
function FlowDiagram({ activeStage }: { activeStage: string | null }) {
  const stages = [
    { id: "draft", label: "Draft", color: "#60a5fa" },
    { id: "critique", label: "Critique", color: "#fb923c" },
    { id: "improvement", label: "Improve", color: "#4ade80" },
  ];

  // We lay three nodes on a circle with arrows between them
  const r = 52;
  const cx = 80;
  const cy = 68;
  const positions = stages.map((_, i) => {
    const angle = (i * 2 * Math.PI) / 3 - Math.PI / 2;
    return { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) };
  });

  return (
    <svg
      viewBox="0 0 160 140"
      style={{ width: 200, height: 175, display: "block", margin: "0 auto" }}
    >
      <defs>
        <marker
          id="arrowSR"
          viewBox="0 0 10 10"
          refX="9"
          refY="5"
          markerWidth="6"
          markerHeight="6"
          orient="auto-start-reverse"
        >
          <path d="M 0 0 L 10 5 L 0 10 z" fill="#a1a1aa" />
        </marker>
      </defs>

      {/* Arrows */}
      {positions.map((from, i) => {
        const to = positions[(i + 1) % 3];
        const dx = to.x - from.x;
        const dy = to.y - from.y;
        const len = Math.sqrt(dx * dx + dy * dy);
        const offsetFrom = 22;
        const offsetTo = 22;
        const x1 = from.x + (dx / len) * offsetFrom;
        const y1 = from.y + (dy / len) * offsetFrom;
        const x2 = to.x - (dx / len) * offsetTo;
        const y2 = to.y - (dy / len) * offsetTo;
        return (
          <line
            key={`arrow-${i}`}
            x1={x1}
            y1={y1}
            x2={x2}
            y2={y2}
            stroke="#a1a1aa"
            strokeWidth={1}
            markerEnd="url(#arrowSR)"
            opacity={0.5}
          />
        );
      })}

      {/* Nodes */}
      {stages.map((s, i) => {
        const pos = positions[i];
        const isActive = activeStage === s.id;
        return (
          <g key={s.id}>
            <circle
              cx={pos.x}
              cy={pos.y}
              r={20}
              fill={isActive ? s.color + "22" : "rgba(255,255,255,0.03)"}
              stroke={isActive ? s.color : "rgba(255,255,255,0.12)"}
              strokeWidth={isActive ? 2 : 1}
            />
            <text
              x={pos.x}
              y={pos.y + 1}
              textAnchor="middle"
              dominantBaseline="middle"
              fill={isActive ? s.color : "#a1a1aa"}
              fontSize={9}
              fontFamily="var(--font-mono), monospace"
              fontWeight={isActive ? 600 : 400}
            >
              {s.label}
            </text>
          </g>
        );
      })}

      {/* "repeat" label in center */}
      <text
        x={cx}
        y={cy}
        textAnchor="middle"
        dominantBaseline="middle"
        fill="#a1a1aa"
        fontSize={7}
        fontFamily="var(--font-mono), monospace"
        opacity={0.5}
      >
        repeat
      </text>
    </svg>
  );
}

/** Phase card inside an iteration */
function PhaseCard({
  phase,
  prevText,
  delay,
}: {
  phase: Phase;
  prevText: string | null;
  delay: number;
}) {
  const badge = phaseBadgeColor(phase.type);
  const isCritique = phase.type === "critique";
  const isImprovement = phase.type === "improvement";

  // Word diff for improvements
  const diffTokens =
    isImprovement && prevText ? wordDiff(prevText, phase.text) : null;

  return (
    <div
      className="animate-fade-in"
      style={{
        animationDelay: `${delay}ms`,
        background: isCritique
          ? "rgba(249,115,22,0.04)"
          : "rgba(255,255,255,0.02)",
        border: "1px solid rgba(255,255,255,0.06)",
        borderRadius: 8,
        padding: "0.75rem 1rem",
        marginBottom: "0.5rem",
      }}
    >
      {/* Badge */}
      <span
        style={{
          display: "inline-block",
          fontSize: "0.6rem",
          fontFamily: "var(--font-mono), monospace",
          fontWeight: 600,
          letterSpacing: "0.08em",
          background: badge.bg,
          color: badge.text,
          padding: "2px 8px",
          borderRadius: 999,
          marginBottom: 8,
        }}
      >
        {badge.label}
      </span>

      {/* Text */}
      <div
        style={{
          fontFamily: isCritique
            ? "var(--font-mono), monospace"
            : "var(--font-sans), system-ui, sans-serif",
          fontSize: isCritique ? "0.78rem" : "0.85rem",
          lineHeight: 1.7,
          color: isCritique ? "#d4a574" : "#e4e4e7",
          whiteSpace: "pre-wrap",
        }}
      >
        {diffTokens
          ? diffTokens.map((t, i) => (
              <span
                key={i}
                style={{
                  color: t.changed ? "#4ade80" : "#e4e4e7",
                  textDecoration: t.changed ? "none" : "none",
                  fontWeight: t.changed ? 600 : 400,
                  background: t.changed
                    ? "rgba(74,222,128,0.08)"
                    : "transparent",
                  borderRadius: t.changed ? 2 : 0,
                  padding: t.changed ? "0 2px" : 0,
                }}
              >
                {t.word}{" "}
              </span>
            ))
          : phase.text}
      </div>
    </div>
  );
}

/** One iteration card */
function IterationCard({
  iteration,
  prevDraftText,
  animDelay,
}: {
  iteration: Iteration;
  prevDraftText: string | null;
  animDelay: number;
}) {
  const sBadge = statusBadge(iteration.status);

  return (
    <div
      className="animate-fade-in"
      style={{
        animationDelay: `${animDelay}ms`,
        background: "rgba(255,255,255,0.015)",
        border: "1px solid rgba(255,255,255,0.06)",
        borderRadius: 10,
        padding: "1rem",
        position: "relative",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "0.75rem",
        }}
      >
        <span
          style={{
            fontFamily: "var(--font-mono), monospace",
            fontSize: "0.75rem",
            fontWeight: 600,
            color: "#e4e4e7",
          }}
        >
          Iteration {iteration.number}
        </span>

        {iteration.status !== "pending" && (
          <span
            style={{
              display: "inline-block",
              fontSize: "0.6rem",
              fontFamily: "var(--font-mono), monospace",
              fontWeight: 600,
              letterSpacing: "0.06em",
              background: sBadge.bg,
              border: `1px solid ${sBadge.border}`,
              color: sBadge.text,
              padding: "2px 8px",
              borderRadius: 999,
            }}
          >
            {sBadge.label}
          </span>
        )}
      </div>

      {/* Phases */}
      {iteration.phases.map((phase, pi) => (
        <PhaseCard
          key={pi}
          phase={phase}
          prevText={
            phase.type === "improvement" ? prevDraftText : null
          }
          delay={animDelay + (pi + 1) * 300}
        />
      ))}
    </div>
  );
}

/** Arrow between iteration cards */
function IterationArrow() {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        padding: "0.5rem 0",
        color: "#a1a1aa",
        opacity: 0.5,
      }}
    >
      <svg
        width="20"
        height="24"
        viewBox="0 0 20 24"
        fill="none"
        style={{ display: "block" }}
      >
        <path
          d="M10 0 L10 18 M4 14 L10 20 L16 14"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Widget                                                        */
/* ------------------------------------------------------------------ */

export function SelfReflectionWidget() {
  const [promptIndex, setPromptIndex] = useState(0);
  const [running, setRunning] = useState(false);
  const [visibleIterations, setVisibleIterations] = useState(0);
  const [activeFlowStage, setActiveFlowStage] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const prompt = PROMPTS[promptIndex];
  const totalIterations = prompt.iterations.length;

  // Avoid hydration mismatch
  useEffect(() => {
    setMounted(true);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  const reset = useCallback(() => {
    setVisibleIterations(0);
    setRunning(false);
    setActiveFlowStage(null);
    if (timerRef.current) clearTimeout(timerRef.current);
  }, []);

  const runReflection = useCallback(() => {
    if (running) return;
    reset();
    setRunning(true);

    // Reveal iterations one at a time, cycling through flow stages
    let step = 0;
    const totalSteps = totalIterations;

    function tick() {
      if (step >= totalSteps) {
        setRunning(false);
        setActiveFlowStage(null);
        return;
      }

      // Determine the main phase type for this iteration
      const iter = prompt.iterations[step];
      const mainPhaseType = iter.phases[0].type;

      // Animate through the phases of this iteration
      setActiveFlowStage(mainPhaseType);
      setVisibleIterations(step + 1);

      // After a brief pause for the first phase, show critique highlight
      timerRef.current = setTimeout(() => {
        setActiveFlowStage("critique");
        timerRef.current = setTimeout(() => {
          // If there's improvement, highlight that
          if (
            iter.phases.some((p) => p.type === "improvement") ||
            step < totalSteps - 1
          ) {
            setActiveFlowStage(
              iter.status === "correct" ? null : "improvement"
            );
          }
          step++;
          timerRef.current = setTimeout(tick, 800);
        }, 1000);
      }, 1200);
    }

    // Tiny delay before starting
    timerRef.current = setTimeout(tick, 300);
  }, [running, totalIterations, prompt, reset]);

  const handlePromptSwitch = useCallback(
    (idx: number) => {
      if (running) return;
      setPromptIndex(idx);
      reset();
    },
    [running, reset]
  );

  // Current turn display
  const currentTurn = visibleIterations || 0;

  if (!mounted) {
    return (
      <div className="widget-container s4">
        <div className="widget-label">
          Interactive &middot; Self-Reflection (Reflexion)
        </div>
        <div style={{ minHeight: 300 }} />
      </div>
    );
  }

  // Determine the previous draft text for diff highlighting
  function getPrevDraftText(iterIndex: number): string | null {
    if (iterIndex === 0) return null;
    const prevIter = prompt.iterations[iterIndex - 1];
    const draftOrImprovement = prevIter.phases.find(
      (p) => p.type === "draft" || p.type === "improvement"
    );
    return draftOrImprovement?.text ?? null;
  }

  return (
    <div className="widget-container s4">
      <div className="widget-label">
        Interactive &middot; Self-Reflection (Reflexion)
      </div>

      {/* Task prompt */}
      <div
        style={{
          background: "rgba(167,139,250,0.06)",
          border: "1px solid rgba(167,139,250,0.15)",
          borderRadius: 8,
          padding: "0.75rem 1rem",
          marginBottom: "1.25rem",
          display: "flex",
          alignItems: "center",
          gap: "0.75rem",
        }}
      >
        <span
          style={{
            fontSize: "0.65rem",
            fontFamily: "var(--font-mono), monospace",
            fontWeight: 600,
            color: "#a78bfa",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            whiteSpace: "nowrap",
          }}
        >
          Task
        </span>
        <span
          style={{
            fontSize: "0.9rem",
            color: "#e4e4e7",
            lineHeight: 1.5,
          }}
        >
          {prompt.label}
        </span>
      </div>

      {/* Flow Diagram + Controls row */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          gap: "1rem",
          marginBottom: "1.25rem",
        }}
      >
        <FlowDiagram activeStage={activeFlowStage} />

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "0.75rem",
            flex: 1,
            minWidth: 200,
          }}
        >
          {/* Turn counter */}
          <div
            style={{
              fontFamily: "var(--font-mono), monospace",
              fontSize: "0.75rem",
              color: "#a1a1aa",
            }}
          >
            Turn{" "}
            <span style={{ color: "#e4e4e7", fontWeight: 600 }}>
              {currentTurn}
            </span>
            /{MAX_TURNS}
          </div>

          {/* Run button */}
          <button
            className="btn-mono"
            onClick={runReflection}
            disabled={running}
            style={{
              opacity: running ? 0.5 : 1,
              cursor: running ? "not-allowed" : "pointer",
              borderColor: running
                ? "rgba(255,255,255,0.08)"
                : "rgba(167,139,250,0.3)",
              color: running ? "#a1a1aa" : "#c4b5fd",
              maxWidth: 180,
            }}
          >
            {running ? "Reflecting..." : "Run Reflection"}
          </button>

          {/* Prompt switcher */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem" }}>
            {PROMPTS.map((p, i) => (
              <button
                key={i}
                className={`btn-mono${i === promptIndex ? " active" : ""}`}
                onClick={() => handlePromptSwitch(i)}
                style={{ fontSize: "0.68rem" }}
                disabled={running}
              >
                Prompt {i + 1}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Iteration cards */}
      <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
        {visibleIterations === 0 && (
          <div
            style={{
              textAlign: "center",
              padding: "2rem 1rem",
              color: "#a1a1aa",
              fontFamily: "var(--font-mono), monospace",
              fontSize: "0.78rem",
              opacity: 0.6,
            }}
          >
            Press &ldquo;Run Reflection&rdquo; to start the Draft &rarr;
            Critique &rarr; Improve loop
          </div>
        )}

        {prompt.iterations.slice(0, visibleIterations).map((iter, i) => (
          <div key={`${promptIndex}-${i}`}>
            {i > 0 && <IterationArrow />}
            <IterationCard
              iteration={iter}
              prevDraftText={getPrevDraftText(i)}
              animDelay={0}
            />
          </div>
        ))}
      </div>

      {/* Summary footer when complete */}
      {visibleIterations === totalIterations &&
        !running &&
        visibleIterations > 0 && (
          <div
            className="animate-fade-in"
            style={{
              marginTop: "1rem",
              padding: "0.75rem 1rem",
              background: "rgba(74,222,128,0.04)",
              border: "1px solid rgba(74,222,128,0.12)",
              borderRadius: 8,
              fontFamily: "var(--font-mono), monospace",
              fontSize: "0.75rem",
              color: "#4ade80",
              textAlign: "center",
            }}
          >
            Reflection complete &mdash; output accepted after{" "}
            {totalIterations} iteration
            {totalIterations > 1 ? "s" : ""}
          </div>
        )}
    </div>
  );
}
