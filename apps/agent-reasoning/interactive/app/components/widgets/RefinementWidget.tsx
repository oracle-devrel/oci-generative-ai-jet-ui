"use client";

import { useState, useCallback, useRef, useEffect } from "react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface IterationData {
  number: number;
  role: "generator" | "critic" | "refiner";
  draft: string;
  score: number;
  feedback: string;
}

/* ------------------------------------------------------------------ */
/*  Static data                                                        */
/* ------------------------------------------------------------------ */

const ITERATIONS: IterationData[] = [
  {
    number: 1,
    role: "generator",
    draft:
      "Quantum entanglement is a phenomenon where two particles become correlated such that the quantum state of one particle instantaneously influences the state of the other, regardless of the distance separating them.",
    score: 0.45,
    feedback: "Too abstract, needs analogy. Uses jargon like 'correlated' and 'quantum state' that a 10-year-old won't understand.",
  },
  {
    number: 2,
    role: "refiner",
    draft:
      "Imagine you have two special socks that are always opposites. If one sock turns red, the other instantly turns blue \u2014 even if your friend took it to the moon! That\u2019s kind of how quantum entanglement works: two tiny particles are connected so that what happens to one affects the other, no matter how far apart they are.",
    score: 0.72,
    feedback: "Better! The sock analogy helps, but 'particles' is still a bit vague. Needs simpler words and a more playful tone.",
  },
  {
    number: 3,
    role: "refiner",
    draft:
      "Imagine you and your friend each have a magic dice. You can be anywhere in the whole universe \u2014 even on different planets! When you roll yours and get a 6, your friend\u2019s dice magically shows a 6 at the exact same moment. Nobody sent a message, nobody peeked \u2014 they\u2019re just connected like magic. Scientists call this 'quantum entanglement', and it\u2019s one of the coolest tricks in nature!",
    score: 0.91,
    feedback: "Excellent! Clear, engaging, and age-appropriate. The magic dice analogy is intuitive and the excited tone matches a 10-year-old\u2019s curiosity.",
  },
  {
    number: 4,
    role: "refiner",
    draft:
      "Imagine you and your best friend each have a magic dice. You could be on opposite sides of the Earth \u2014 or even different galaxies! When you roll yours and get a 6, your friend\u2019s dice instantly lands on 6 too. No phone call, no Wi-Fi, no trick \u2014 they just always match, like they\u2019re sharing a secret. Scientists discovered this real-life magic and named it 'quantum entanglement'. It\u2019s one of nature\u2019s most amazing surprises, and even grown-up scientists think it\u2019s wild!",
    score: 0.96,
    feedback: "Outstanding! Even more polished: relatable references (Wi-Fi, phone call), delightful closing, and perfectly tuned for a 10-year-old audience.",
  },
];

const TASK = "Explain quantum entanglement to a 10-year-old";

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

/** Return a CSS color along the red-yellow-green gradient for 0..1 */
function scoreColor(score: number): string {
  if (score < 0.5) {
    // red to yellow
    const t = score / 0.5;
    const r = 239;
    const g = Math.round(68 + (190 - 68) * t);
    const b = Math.round(68 * (1 - t));
    return `rgb(${r},${g},${b})`;
  }
  // yellow to green
  const t = (score - 0.5) / 0.5;
  const r = Math.round(239 - (239 - 74) * t);
  const g = Math.round(190 + (222 - 190) * t);
  const b = Math.round(0 + 128 * t);
  return `rgb(${r},${g},${b})`;
}

function scoreGradient(score: number): string {
  const endColor = scoreColor(score);
  return `linear-gradient(90deg, ${scoreColor(0)}, ${endColor})`;
}

function roleBadge(role: IterationData["role"]): {
  bg: string;
  text: string;
  label: string;
  icon: string;
} {
  switch (role) {
    case "generator":
      return {
        bg: "rgba(59,130,246,0.15)",
        text: "#60a5fa",
        label: "GENERATOR",
        icon: "\u270D",
      };
    case "critic":
      return {
        bg: "rgba(249,115,22,0.15)",
        text: "#fb923c",
        label: "CRITIC",
        icon: "\uD83D\uDD0D",
      };
    case "refiner":
      return {
        bg: "rgba(74,222,128,0.15)",
        text: "#4ade80",
        label: "REFINER",
        icon: "\u2728",
      };
  }
}

/* ------------------------------------------------------------------ */
/*  Sub-components                                                     */
/* ------------------------------------------------------------------ */

/** Role badges row */
function RoleBadges() {
  const roles: IterationData["role"][] = ["generator", "critic", "refiner"];
  return (
    <div style={{ display: "flex", gap: "0.6rem", flexWrap: "wrap" }}>
      {roles.map((r) => {
        const b = roleBadge(r);
        return (
          <div
            key={r}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.35rem",
              background: b.bg,
              border: `1px solid ${b.text}33`,
              borderRadius: 999,
              padding: "0.25rem 0.7rem",
              fontSize: "0.68rem",
              fontFamily: "var(--font-mono), monospace",
              fontWeight: 600,
              color: b.text,
              letterSpacing: "0.05em",
            }}
          >
            <span style={{ fontSize: "0.8rem" }}>{b.icon}</span>
            {b.label}
          </div>
        );
      })}
    </div>
  );
}

/** Small sparkline SVG showing score progression */
function Sparkline({
  scores,
  threshold,
}: {
  scores: number[];
  threshold: number;
}) {
  if (scores.length === 0) return null;

  const w = 160;
  const h = 48;
  const padX = 12;
  const padY = 6;
  const innerW = w - padX * 2;
  const innerH = h - padY * 2;

  const points = scores.map((s, i) => ({
    x: padX + (scores.length === 1 ? innerW / 2 : (i / (scores.length - 1)) * innerW),
    y: padY + (1 - s) * innerH,
  }));

  const polyline = points.map((p) => `${p.x},${p.y}`).join(" ");
  const thresholdY = padY + (1 - threshold) * innerH;

  return (
    <svg
      viewBox={`0 0 ${w} ${h}`}
      style={{ width: w, height: h, display: "block" }}
    >
      {/* Threshold line */}
      <line
        x1={padX}
        y1={thresholdY}
        x2={w - padX}
        y2={thresholdY}
        stroke="#f472b6"
        strokeWidth={1}
        strokeDasharray="4 3"
        opacity={0.7}
      />

      {/* Score line */}
      <polyline
        fill="none"
        stroke="#e4e4e7"
        strokeWidth={1.5}
        points={polyline}
        strokeLinejoin="round"
      />

      {/* Dots */}
      {points.map((p, i) => (
        <circle
          key={i}
          cx={p.x}
          cy={p.y}
          r={3}
          fill={scoreColor(scores[i])}
          stroke="rgba(0,0,0,0.5)"
          strokeWidth={0.5}
        />
      ))}

      {/* Score labels */}
      {points.map((p, i) => (
        <text
          key={`lbl-${i}`}
          x={p.x}
          y={p.y - 7}
          textAnchor="middle"
          fill={scoreColor(scores[i])}
          fontSize={7}
          fontFamily="var(--font-mono), monospace"
          fontWeight={600}
        >
          {scores[i].toFixed(2)}
        </text>
      ))}
    </svg>
  );
}

/** Arrow between iteration cards */
function IterationArrow() {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        padding: "0.35rem 0",
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

/** Single iteration card */
function IterationCard({
  iteration,
  threshold,
  animDelay,
}: {
  iteration: IterationData;
  threshold: number;
  animDelay: number;
}) {
  const meetsThreshold = iteration.score >= threshold;
  const badge = iteration.number === 1 ? roleBadge("generator") : roleBadge("refiner");
  const criticBadge = roleBadge("critic");
  const barWidth = Math.round(iteration.score * 100);

  return (
    <div
      className="animate-fade-in"
      style={{
        animationDelay: `${animDelay}ms`,
        background: meetsThreshold
          ? "rgba(74,222,128,0.04)"
          : "rgba(255,255,255,0.015)",
        border: meetsThreshold
          ? "1px solid rgba(74,222,128,0.25)"
          : "1px solid rgba(255,255,255,0.06)",
        borderRadius: 10,
        padding: "1rem",
        position: "relative",
        boxShadow: meetsThreshold
          ? "0 0 20px rgba(74,222,128,0.1), inset 0 0 20px rgba(74,222,128,0.03)"
          : "none",
        transition: "border-color 0.3s, box-shadow 0.3s, background 0.3s",
      }}
    >
      {/* Header row */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "0.75rem",
          flexWrap: "wrap",
          gap: "0.5rem",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
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
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "0.25rem",
              fontSize: "0.6rem",
              fontFamily: "var(--font-mono), monospace",
              fontWeight: 600,
              letterSpacing: "0.06em",
              background: badge.bg,
              color: badge.text,
              padding: "2px 8px",
              borderRadius: 999,
            }}
          >
            <span style={{ fontSize: "0.7rem" }}>{badge.icon}</span>
            {badge.label}
          </span>
        </div>

        {/* Score pill */}
        <span
          style={{
            fontFamily: "var(--font-mono), monospace",
            fontSize: "0.8rem",
            fontWeight: 700,
            color: scoreColor(iteration.score),
          }}
        >
          {iteration.score.toFixed(2)}
        </span>
      </div>

      {/* Draft text */}
      <div
        style={{
          background: "rgba(255,255,255,0.02)",
          border: "1px solid rgba(255,255,255,0.05)",
          borderRadius: 8,
          padding: "0.7rem 0.85rem",
          marginBottom: "0.65rem",
          fontSize: "0.83rem",
          lineHeight: 1.7,
          color: "#e4e4e7",
        }}
      >
        {iteration.draft}
      </div>

      {/* Score bar with threshold */}
      <div style={{ marginBottom: "0.65rem" }}>
        <div
          style={{
            position: "relative",
            height: 10,
            background: "rgba(255,255,255,0.06)",
            borderRadius: 5,
            overflow: "visible",
          }}
        >
          {/* Filled bar */}
          <div
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              height: "100%",
              width: `${barWidth}%`,
              background: scoreGradient(iteration.score),
              borderRadius: 5,
              transition: "width 0.6s ease-out",
            }}
          />
          {/* Threshold marker */}
          <div
            style={{
              position: "absolute",
              top: -3,
              left: `${Math.round(threshold * 100)}%`,
              width: 0,
              height: 16,
              borderLeft: "2px dashed #f472b6",
              transform: "translateX(-1px)",
              opacity: 0.8,
            }}
          />
        </div>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            marginTop: 4,
            fontSize: "0.6rem",
            fontFamily: "var(--font-mono), monospace",
            color: "#a1a1aa",
          }}
        >
          <span>0.0</span>
          <span style={{ color: "#f472b6", opacity: 0.8 }}>
            threshold: {threshold.toFixed(2)}
          </span>
          <span>1.0</span>
        </div>
      </div>

      {/* Critic feedback */}
      <div
        style={{
          background: "rgba(249,115,22,0.04)",
          border: "1px solid rgba(249,115,22,0.1)",
          borderRadius: 8,
          padding: "0.6rem 0.85rem",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.35rem",
            marginBottom: "0.35rem",
          }}
        >
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "0.2rem",
              fontSize: "0.58rem",
              fontFamily: "var(--font-mono), monospace",
              fontWeight: 600,
              letterSpacing: "0.06em",
              background: criticBadge.bg,
              color: criticBadge.text,
              padding: "2px 6px",
              borderRadius: 999,
            }}
          >
            <span style={{ fontSize: "0.65rem" }}>{criticBadge.icon}</span>
            FEEDBACK
          </span>
        </div>
        <div
          style={{
            fontFamily: "var(--font-mono), monospace",
            fontSize: "0.76rem",
            lineHeight: 1.6,
            color: "#d4a574",
          }}
        >
          {iteration.feedback}
        </div>
      </div>

      {/* Passed badge */}
      {meetsThreshold && (
        <div
          style={{
            position: "absolute",
            top: 8,
            right: 8,
            fontSize: "0.58rem",
            fontFamily: "var(--font-mono), monospace",
            fontWeight: 700,
            letterSpacing: "0.08em",
            background: "rgba(74,222,128,0.12)",
            border: "1px solid rgba(74,222,128,0.3)",
            color: "#4ade80",
            padding: "2px 8px",
            borderRadius: 999,
          }}
        >
          PASSED
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Flow Diagram: Generator -> Critic -> Refiner                       */
/* ------------------------------------------------------------------ */

function FlowDiagram({ activeStage }: { activeStage: string | null }) {
  const stages = [
    { id: "generator", label: "Generator", color: "#60a5fa", icon: "\u270D" },
    { id: "critic", label: "Critic", color: "#fb923c", icon: "\uD83D\uDD0D" },
    { id: "refiner", label: "Refiner", color: "#4ade80", icon: "\u2728" },
  ];

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
      style={{ width: 200, height: 175, display: "block", flexShrink: 0 }}
    >
      <defs>
        <marker
          id="arrowRW"
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
            markerEnd="url(#arrowRW)"
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
              fontSize={8}
              fontFamily="var(--font-mono), monospace"
              fontWeight={isActive ? 600 : 400}
            >
              {s.label}
            </text>
          </g>
        );
      })}

      {/* Center label */}
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
        score loop
      </text>
    </svg>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Widget                                                        */
/* ------------------------------------------------------------------ */

export function RefinementWidget() {
  const [threshold, setThreshold] = useState(0.8);
  const [running, setRunning] = useState(false);
  const [visibleIterations, setVisibleIterations] = useState(0);
  const [activeFlowStage, setActiveFlowStage] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Decide how many iterations to show based on threshold
  const needsExtraIteration = threshold > 0.91;
  const allIterations = needsExtraIteration ? ITERATIONS : ITERATIONS.slice(0, 3);
  const totalIterations = allIterations.length;

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

  const runRefinement = useCallback(() => {
    if (running) return;
    reset();
    setRunning(true);

    let step = 0;

    function tick() {
      if (step >= totalIterations) {
        setRunning(false);
        setActiveFlowStage(null);
        return;
      }

      const iter = allIterations[step];

      // Animate role stages
      if (step === 0) {
        setActiveFlowStage("generator");
      } else {
        setActiveFlowStage("refiner");
      }

      timerRef.current = setTimeout(() => {
        setVisibleIterations(step + 1);
        setActiveFlowStage("critic");

        timerRef.current = setTimeout(() => {
          // Check if this iteration passes threshold
          if (iter.score >= threshold) {
            setActiveFlowStage(null);
            step = totalIterations; // Done
            timerRef.current = setTimeout(() => {
              setRunning(false);
            }, 400);
          } else {
            step++;
            timerRef.current = setTimeout(tick, 300);
          }
        }, 700);
      }, 700);
    }

    timerRef.current = setTimeout(tick, 300);
  }, [running, totalIterations, allIterations, threshold, reset]);

  const handleThresholdChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (running) return;
      setThreshold(parseFloat(e.target.value));
      reset();
    },
    [running, reset]
  );

  // Determine which iterations are visible and what scores to show in sparkline
  const visibleIters = allIterations.slice(0, visibleIterations);
  const visibleScores = visibleIters.map((it) => it.score);

  // Find the first iteration that meets threshold (for the completion message)
  const passedIter = visibleIters.find((it) => it.score >= threshold);

  if (!mounted) {
    return (
      <div className="widget-container s5">
        <div className="widget-label">
          Interactive &middot; Iterative Refinement Loop
        </div>
        <div style={{ minHeight: 300 }} />
      </div>
    );
  }

  return (
    <div className="widget-container s5">
      <div className="widget-label">
        Interactive &middot; Iterative Refinement Loop
      </div>

      {/* Task prompt */}
      <div
        style={{
          background: "rgba(244,114,182,0.06)",
          border: "1px solid rgba(244,114,182,0.15)",
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
            color: "#f472b6",
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
          {TASK}
        </span>
      </div>

      {/* Role badges */}
      <div style={{ marginBottom: "1.25rem" }}>
        <RoleBadges />
      </div>

      {/* Flow diagram + controls */}
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
            gap: "0.85rem",
            flex: 1,
            minWidth: 200,
          }}
        >
          {/* Threshold slider */}
          <div>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                marginBottom: "0.4rem",
              }}
            >
              <span
                style={{
                  fontFamily: "var(--font-mono), monospace",
                  fontSize: "0.72rem",
                  color: "#a1a1aa",
                }}
              >
                Score Threshold
              </span>
              <span
                style={{
                  fontFamily: "var(--font-mono), monospace",
                  fontSize: "0.78rem",
                  fontWeight: 700,
                  color: "#f472b6",
                }}
              >
                {threshold.toFixed(2)}
              </span>
            </div>
            <input
              type="range"
              min={0.5}
              max={1.0}
              step={0.01}
              value={threshold}
              onChange={handleThresholdChange}
              disabled={running}
              style={{ opacity: running ? 0.5 : 1 }}
            />
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                fontSize: "0.58rem",
                fontFamily: "var(--font-mono), monospace",
                color: "#a1a1aa",
                marginTop: 2,
              }}
            >
              <span>0.50</span>
              <span>1.00</span>
            </div>
          </div>

          {/* Run button */}
          <button
            className="btn-mono"
            onClick={runRefinement}
            disabled={running}
            style={{
              opacity: running ? 0.5 : 1,
              cursor: running ? "not-allowed" : "pointer",
              borderColor: running
                ? "rgba(255,255,255,0.08)"
                : "rgba(244,114,182,0.3)",
              color: running ? "#a1a1aa" : "#f9a8d4",
              maxWidth: 200,
            }}
          >
            {running ? "Refining..." : "Run Refinement"}
          </button>

          {/* Score trend sparkline */}
          {visibleScores.length > 0 && (
            <div>
              <span
                style={{
                  fontFamily: "var(--font-mono), monospace",
                  fontSize: "0.65rem",
                  color: "#a1a1aa",
                  marginBottom: 4,
                  display: "block",
                }}
              >
                Score Trend
              </span>
              <div
                style={{
                  background: "rgba(255,255,255,0.02)",
                  border: "1px solid rgba(255,255,255,0.06)",
                  borderRadius: 8,
                  padding: "0.4rem 0.5rem",
                  display: "inline-block",
                }}
              >
                <Sparkline scores={visibleScores} threshold={threshold} />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Iteration cards */}
      <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
        {visibleIterations === 0 && !running && (
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
            Press &ldquo;Run Refinement&rdquo; to start the Generator &rarr;
            Critic &rarr; Refiner loop
          </div>
        )}

        {visibleIters.map((iter, i) => (
          <div key={`iter-${iter.number}`}>
            {i > 0 && <IterationArrow />}
            <IterationCard
              iteration={iter}
              threshold={threshold}
              animDelay={0}
            />
          </div>
        ))}
      </div>

      {/* Completion footer */}
      {passedIter && !running && (
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
          Refinement complete &mdash; score {passedIter.score.toFixed(2)}{" "}
          {"\u2265"} threshold {threshold.toFixed(2)} after{" "}
          {passedIter.number} iteration
          {passedIter.number > 1 ? "s" : ""}
        </div>
      )}

      {/* All iterations exhausted without passing */}
      {visibleIterations === totalIterations &&
        !running &&
        !passedIter &&
        visibleIterations > 0 && (
          <div
            className="animate-fade-in"
            style={{
              marginTop: "1rem",
              padding: "0.75rem 1rem",
              background: "rgba(239,68,68,0.04)",
              border: "1px solid rgba(239,68,68,0.12)",
              borderRadius: 8,
              fontFamily: "var(--font-mono), monospace",
              fontSize: "0.75rem",
              color: "#f87171",
              textAlign: "center",
            }}
          >
            Threshold {threshold.toFixed(2)} not reached after{" "}
            {totalIterations} iterations &mdash; best score:{" "}
            {Math.max(...visibleScores).toFixed(2)}
          </div>
        )}
    </div>
  );
}
