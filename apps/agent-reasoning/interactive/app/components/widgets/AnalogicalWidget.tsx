"use client";

import { useState, useCallback, useRef, useEffect } from "react";

/* ------------------------------------------------------------------ */
/*  Types & Data                                                       */
/* ------------------------------------------------------------------ */

interface StructuralElement {
  label: string;
  description: string;
}

interface Analogy {
  domain: string;
  icon: string; // SVG path data
  title: string;
  description: string;
  color: string;
  relevance: number; // 0-1
}

interface Mapping {
  source: string;
  target: string;
}

const STRUCTURAL_ELEMENTS: StructuralElement[] = [
  { label: "Nodes", description: "Discrete points that send/receive items" },
  { label: "Routes", description: "Paths connecting nodes with capacity constraints" },
  { label: "Optimization", description: "Minimizing cost while maximizing coverage" },
  { label: "Throughput", description: "Volume of items delivered per time unit" },
];

const ANALOGIES: Analogy[] = [
  {
    domain: "Biology",
    icon: "M9 3C9 3 7 5 7 8C7 11 9 12 9 12C9 12 11 11 11 8C11 5 9 3 9 3Z M9 12V19 M6 15H12 M5 17H13",
    title: "Circulatory System",
    description:
      "Blood vessels branch from arteries to capillaries for efficient distribution to every cell",
    color: "#f43f5e",
    relevance: 0.92,
  },
  {
    domain: "Computer Science",
    icon: "M3 6H9V12H3Z M11 6H17V12H11Z M7 14H13V20H7Z M6 12V14 M14 12L10 14",
    title: "Network Routing",
    description:
      "Packets find optimal paths via routing tables and load balancing across network topology",
    color: "#22d3ee",
    relevance: 0.78,
  },
  {
    domain: "Nature",
    icon: "M10 4C10 4 5 8 5 12C5 16 10 18 10 18C10 18 15 16 15 12C15 8 10 4 10 4Z M7 10L13 10 M8 13L12 13 M10 8V15",
    title: "Ant Colonies",
    description:
      "Pheromone trails create self-optimizing paths to food sources through emergent behavior",
    color: "#4ade80",
    relevance: 0.85,
  },
];

const MAPPINGS: Mapping[] = [
  { source: "Arteries", target: "Main distribution hubs" },
  { source: "Capillaries", target: "Last-mile delivery routes" },
  { source: "Blood pressure", target: "Delivery priority/urgency" },
  { source: "Heart pump", target: "Central sorting facility" },
];

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const MONO = "var(--font-mono), monospace";
const YELLOW = "#facc15";
const YELLOW_DIM = "rgba(250,204,21,0.5)";
const BG_SUBTLE = "rgba(255,255,255,0.03)";
const BORDER = "rgba(255,255,255,0.08)";
const TEXT = "#e4e4e7";
const MUTED = "#a1a1aa";

type Phase = "idle" | "structure" | "analogies" | "transfer" | "done";

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function AnalogicalWidget() {
  /* --- Hydration guard -------------------------------------------- */
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  /* --- State ------------------------------------------------------ */
  const [phase, setPhase] = useState<Phase>("idle");
  const [visibleElements, setVisibleElements] = useState(0);
  const [visibleAnalogies, setVisibleAnalogies] = useState(0);
  const [selectedAnalogy, setSelectedAnalogy] = useState(-1);
  const [showMappings, setShowMappings] = useState(false);
  const [visibleMappings, setVisibleMappings] = useState(0);

  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);
  const mappingContainerRef = useRef<HTMLDivElement>(null);
  const leftRefs = useRef<(HTMLDivElement | null)[]>([]);
  const rightRefs = useRef<(HTMLDivElement | null)[]>([]);
  const [lineCoords, setLineCoords] = useState<
    { x1: number; y1: number; x2: number; y2: number }[]
  >([]);

  /* --- Timer cleanup ---------------------------------------------- */
  const clearTimers = useCallback(() => {
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];
  }, []);

  useEffect(() => clearTimers, [clearTimers]);

  /* --- Calculate SVG line coords ---------------------------------- */
  const recalcLines = useCallback(() => {
    if (!mappingContainerRef.current) return;
    const containerRect = mappingContainerRef.current.getBoundingClientRect();
    const coords: { x1: number; y1: number; x2: number; y2: number }[] = [];

    for (let i = 0; i < MAPPINGS.length; i++) {
      const leftEl = leftRefs.current[i];
      const rightEl = rightRefs.current[i];
      if (!leftEl || !rightEl) continue;

      const lr = leftEl.getBoundingClientRect();
      const rr = rightEl.getBoundingClientRect();

      coords.push({
        x1: lr.right - containerRect.left,
        y1: lr.top + lr.height / 2 - containerRect.top,
        x2: rr.left - containerRect.left,
        y2: rr.top + rr.height / 2 - containerRect.top,
      });
    }

    setLineCoords(coords);
  }, []);

  useEffect(() => {
    if (showMappings && visibleMappings > 0) {
      // Small delay to let DOM settle after fade-in animation
      const t = setTimeout(recalcLines, 60);
      return () => clearTimeout(t);
    }
  }, [showMappings, visibleMappings, recalcLines]);

  // Recalculate on window resize
  useEffect(() => {
    if (!showMappings) return;
    const handler = () => recalcLines();
    window.addEventListener("resize", handler);
    return () => window.removeEventListener("resize", handler);
  }, [showMappings, recalcLines]);

  /* --- Reset ------------------------------------------------------ */
  const reset = useCallback(() => {
    clearTimers();
    setPhase("idle");
    setVisibleElements(0);
    setVisibleAnalogies(0);
    setSelectedAnalogy(-1);
    setShowMappings(false);
    setVisibleMappings(0);
    setLineCoords([]);
  }, [clearTimers]);

  /* --- Run the 3-phase process ------------------------------------ */
  const findAnalogies = useCallback(() => {
    reset();
    setPhase("structure");

    let delay = 400;

    // Phase 1: Reveal structural elements one by one
    STRUCTURAL_ELEMENTS.forEach((_, i) => {
      const d = delay;
      const t = setTimeout(() => {
        setVisibleElements(i + 1);
      }, d);
      timersRef.current.push(t);
      delay += 350;
    });

    // Transition to Phase 2
    delay += 400;
    const t2 = setTimeout(() => {
      setPhase("analogies");
    }, delay);
    timersRef.current.push(t2);
    delay += 300;

    // Phase 2: Reveal analogy cards one by one
    ANALOGIES.forEach((_, i) => {
      const d = delay;
      const t = setTimeout(() => {
        setVisibleAnalogies(i + 1);
      }, d);
      timersRef.current.push(t);
      delay += 600;
    });

    // Highlight best analogy (highest relevance = Biology at 0.92)
    delay += 500;
    const tSelect = setTimeout(() => {
      setSelectedAnalogy(0); // Biology has highest relevance
    }, delay);
    timersRef.current.push(tSelect);

    // Transition to Phase 3
    delay += 600;
    const t3 = setTimeout(() => {
      setPhase("transfer");
      setShowMappings(true);
    }, delay);
    timersRef.current.push(t3);
    delay += 200;

    // Phase 3: Reveal mappings one by one
    MAPPINGS.forEach((_, i) => {
      const d = delay;
      const t = setTimeout(() => {
        setVisibleMappings(i + 1);
      }, d);
      timersRef.current.push(t);
      delay += 450;
    });

    // Done
    delay += 300;
    const tDone = setTimeout(() => {
      setPhase("done");
    }, delay);
    timersRef.current.push(tDone);
  }, [reset]);

  /* ---------------------------------------------------------------- */
  /*  Phase badge helper                                               */
  /* ---------------------------------------------------------------- */

  const phaseOrder: Phase[] = ["structure", "analogies", "transfer"];
  const phaseLabels = ["Identify Structure", "Generate Analogies", "Transfer Solution"];

  function isPhaseActive(p: Phase): boolean {
    const idx = phaseOrder.indexOf(p);
    const currentIdx = phaseOrder.indexOf(phase);
    if (phase === "done") return true;
    return idx >= 0 && currentIdx >= 0 && idx <= currentIdx;
  }

  function isCurrentPhase(p: Phase): boolean {
    if (phase === "done") return p === "transfer";
    return p === phase;
  }

  /* ---------------------------------------------------------------- */
  /*  Render                                                           */
  /* ---------------------------------------------------------------- */

  const isRunning = phase !== "idle" && phase !== "done";

  return (
    <div className="widget-container s6">
      <div className="widget-label">Interactive &middot; Analogical Reasoning</div>

      {/* ---- Problem statement ---- */}
      <div
        className="rounded-lg p-4 mb-5"
        style={{
          background: BG_SUBTLE,
          border: `1px solid ${BORDER}`,
        }}
      >
        <span
          className="block mb-1"
          style={{
            fontFamily: MONO,
            fontSize: "0.7rem",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            color: MUTED,
          }}
        >
          Novel Problem
        </span>
        <p style={{ color: TEXT, margin: 0, lineHeight: 1.7, fontSize: "0.95rem" }}>
          How can we design a more efficient package delivery network for a city?
        </p>
      </div>

      {/* ---- Phase badges ---- */}
      {phase !== "idle" && (
        <div className="flex flex-wrap items-center gap-2 mb-5 animate-fade-in">
          {phaseOrder.map((p, i) => {
            const active = isPhaseActive(p);
            const current = isCurrentPhase(p);
            return (
              <div
                key={p}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "0.4rem",
                  padding: "0.25rem 0.65rem",
                  borderRadius: 20,
                  fontFamily: MONO,
                  fontSize: "0.68rem",
                  letterSpacing: "0.04em",
                  border: `1px solid ${
                    current
                      ? "rgba(250,204,21,0.4)"
                      : active
                      ? "rgba(250,204,21,0.2)"
                      : BORDER
                  }`,
                  background: current
                    ? "rgba(250,204,21,0.1)"
                    : "transparent",
                  color: active ? YELLOW : MUTED,
                  transition: "all 0.3s",
                }}
              >
                <span
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    width: 18,
                    height: 18,
                    borderRadius: "50%",
                    background: active
                      ? "rgba(250,204,21,0.2)"
                      : "rgba(255,255,255,0.06)",
                    fontSize: "0.62rem",
                    fontWeight: 700,
                    color: active ? YELLOW : MUTED,
                  }}
                >
                  {i + 1}
                </span>
                {phaseLabels[i]}
              </div>
            );
          })}
        </div>
      )}

      {/* ---- Controls ---- */}
      <div className="flex flex-wrap items-center gap-3 mb-6">
        <button
          className="btn-mono"
          onClick={findAnalogies}
          disabled={isRunning}
          style={{
            background: isRunning ? "transparent" : "rgba(250,204,21,0.12)",
            borderColor: isRunning
              ? BORDER
              : "rgba(250,204,21,0.35)",
            color: isRunning ? MUTED : YELLOW,
            cursor: isRunning ? "not-allowed" : "pointer",
          }}
        >
          {isRunning ? "Searching\u2026" : "Find Analogies"}
        </button>

        <button className="btn-mono" onClick={reset}>
          Reset
        </button>
      </div>

      {/* ---- Phase 1: Structural Elements ---- */}
      {phase !== "idle" && (
        <div className="mb-6 animate-fade-in">
          <span
            className="block mb-3"
            style={{
              fontFamily: MONO,
              fontSize: "0.7rem",
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              color: YELLOW,
              fontWeight: 600,
            }}
          >
            Structural Elements Identified
          </span>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
              gap: "0.5rem",
            }}
          >
            {STRUCTURAL_ELEMENTS.map((el, i) => {
              const visible = i < visibleElements;
              return (
                <div
                  key={el.label}
                  className={visible ? "animate-fade-in" : ""}
                  style={{
                    opacity: visible ? 1 : 0,
                    transform: visible ? "translateY(0)" : "translateY(8px)",
                    transition:
                      "opacity 0.4s ease-out, transform 0.4s ease-out",
                    background: visible
                      ? "rgba(250,204,21,0.05)"
                      : BG_SUBTLE,
                    border: `1px solid ${
                      visible ? "rgba(250,204,21,0.2)" : BORDER
                    }`,
                    borderRadius: 8,
                    padding: "0.65rem 0.75rem",
                  }}
                >
                  <span
                    style={{
                      fontFamily: MONO,
                      fontSize: "0.72rem",
                      fontWeight: 700,
                      color: visible ? YELLOW : MUTED,
                    }}
                  >
                    {el.label}
                  </span>
                  <p
                    style={{
                      color: MUTED,
                      margin: "0.25rem 0 0",
                      fontSize: "0.78rem",
                      lineHeight: 1.5,
                    }}
                  >
                    {el.description}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ---- Phase 2: Analogy Cards ---- */}
      {(phase === "analogies" ||
        phase === "transfer" ||
        phase === "done") && (
        <div className="mb-6 animate-fade-in">
          <span
            className="block mb-3"
            style={{
              fontFamily: MONO,
              fontSize: "0.7rem",
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              color: YELLOW,
              fontWeight: 600,
            }}
          >
            Analogies from Other Domains
          </span>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
              gap: "0.75rem",
            }}
          >
            {ANALOGIES.map((analogy, i) => {
              const visible = i < visibleAnalogies;
              const isBest = selectedAnalogy === i;
              return (
                <div
                  key={analogy.domain}
                  className={visible ? "animate-fade-in" : ""}
                  style={{
                    opacity: visible ? 1 : 0,
                    transform: visible ? "translateY(0)" : "translateY(12px)",
                    transition:
                      "opacity 0.5s ease-out, transform 0.5s ease-out, box-shadow 0.5s ease-out",
                    background: isBest
                      ? `rgba(${hexToRgb(analogy.color)},0.06)`
                      : BG_SUBTLE,
                    border: `1px solid ${
                      isBest
                        ? `rgba(${hexToRgb(analogy.color)},0.35)`
                        : BORDER
                    }`,
                    borderTop: `3px solid ${
                      visible ? analogy.color : "transparent"
                    }`,
                    borderRadius: 8,
                    padding: "0.85rem 0.9rem",
                    position: "relative",
                    boxShadow: isBest
                      ? `0 0 24px rgba(${hexToRgb(analogy.color)},0.15)`
                      : "none",
                  }}
                >
                  {/* Best badge */}
                  {isBest && (
                    <span
                      className="animate-fade-in"
                      style={{
                        position: "absolute",
                        top: 8,
                        right: 8,
                        fontFamily: MONO,
                        fontSize: "0.58rem",
                        textTransform: "uppercase",
                        letterSpacing: "0.06em",
                        background: `rgba(${hexToRgb(analogy.color)},0.15)`,
                        color: analogy.color,
                        padding: "0.15rem 0.45rem",
                        borderRadius: 10,
                        fontWeight: 700,
                      }}
                    >
                      Best Match
                    </span>
                  )}

                  {/* Domain icon + label */}
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "0.45rem",
                      marginBottom: "0.4rem",
                    }}
                  >
                    {mounted && (
                      <svg
                        width="18"
                        height="18"
                        viewBox="0 0 20 20"
                        fill="none"
                        xmlns="http://www.w3.org/2000/svg"
                      >
                        <path
                          d={analogy.icon}
                          stroke={analogy.color}
                          strokeWidth="1.3"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          fill="none"
                        />
                      </svg>
                    )}
                    <span
                      style={{
                        fontFamily: MONO,
                        fontSize: "0.65rem",
                        textTransform: "uppercase",
                        letterSpacing: "0.06em",
                        color: analogy.color,
                        fontWeight: 700,
                      }}
                    >
                      {analogy.domain}
                    </span>
                  </div>

                  {/* Title */}
                  <p
                    style={{
                      fontFamily: MONO,
                      fontSize: "0.85rem",
                      fontWeight: 600,
                      color: TEXT,
                      margin: "0 0 0.3rem",
                    }}
                  >
                    {analogy.title}
                  </p>

                  {/* Description */}
                  <p
                    style={{
                      color: MUTED,
                      margin: "0 0 0.65rem",
                      fontSize: "0.8rem",
                      lineHeight: 1.55,
                    }}
                  >
                    {analogy.description}
                  </p>

                  {/* Relevance score bar */}
                  <div>
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        marginBottom: "0.25rem",
                      }}
                    >
                      <span
                        style={{
                          fontFamily: MONO,
                          fontSize: "0.62rem",
                          color: MUTED,
                          textTransform: "uppercase",
                          letterSpacing: "0.04em",
                        }}
                      >
                        Relevance
                      </span>
                      <span
                        style={{
                          fontFamily: MONO,
                          fontSize: "0.68rem",
                          color: analogy.color,
                          fontWeight: 600,
                        }}
                      >
                        {visible
                          ? `${Math.round(analogy.relevance * 100)}%`
                          : "--"}
                      </span>
                    </div>
                    <div
                      style={{
                        height: 5,
                        borderRadius: 3,
                        background: "rgba(255,255,255,0.06)",
                        overflow: "hidden",
                      }}
                    >
                      <div
                        style={{
                          width: visible
                            ? `${analogy.relevance * 100}%`
                            : "0%",
                          height: "100%",
                          borderRadius: 3,
                          background: `linear-gradient(90deg, ${analogy.color}, rgba(${hexToRgb(analogy.color)},0.4))`,
                          transition: "width 0.7s ease-out",
                        }}
                      />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ---- Phase 3: Transfer Mapping ---- */}
      {showMappings && (
        <div className="animate-fade-in">
          <span
            className="block mb-3"
            style={{
              fontFamily: MONO,
              fontSize: "0.7rem",
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              color: YELLOW,
              fontWeight: 600,
            }}
          >
            Solution Transfer: Circulatory System → Delivery Network
          </span>

          <div
            ref={mappingContainerRef}
            style={{
              position: "relative",
              display: "grid",
              gridTemplateColumns: "1fr auto 1fr",
              gap: "0.5rem",
              padding: "1rem",
              background: "rgba(0,0,0,0.25)",
              border: `1px solid ${BORDER}`,
              borderRadius: 10,
            }}
          >
            {/* Column headers */}
            <div
              style={{
                fontFamily: MONO,
                fontSize: "0.65rem",
                textTransform: "uppercase",
                letterSpacing: "0.06em",
                color: "#f43f5e",
                fontWeight: 700,
                marginBottom: "0.35rem",
                textAlign: "center",
              }}
            >
              Source Analogy
            </div>
            <div />
            <div
              style={{
                fontFamily: MONO,
                fontSize: "0.65rem",
                textTransform: "uppercase",
                letterSpacing: "0.06em",
                color: YELLOW,
                fontWeight: 700,
                marginBottom: "0.35rem",
                textAlign: "center",
              }}
            >
              Target Problem
            </div>

            {/* SVG connector overlay */}
            {mounted && lineCoords.length > 0 && (
              <svg
                style={{
                  position: "absolute",
                  top: 0,
                  left: 0,
                  width: "100%",
                  height: "100%",
                  pointerEvents: "none",
                  zIndex: 1,
                }}
              >
                {lineCoords.map((c, i) => {
                  if (i >= visibleMappings) return null;
                  const midX = (c.x1 + c.x2) / 2;
                  return (
                    <path
                      key={`line-${i}`}
                      d={`M ${c.x1} ${c.y1} C ${midX} ${c.y1}, ${midX} ${c.y2}, ${c.x2} ${c.y2}`}
                      stroke="rgba(250,204,21,0.35)"
                      strokeWidth="1.5"
                      fill="none"
                      strokeDasharray="4 3"
                      style={{
                        opacity: 1,
                        transition: "opacity 0.4s ease-out",
                      }}
                    />
                  );
                })}
              </svg>
            )}

            {/* Mapping rows */}
            {MAPPINGS.map((mapping, i) => {
              const visible = i < visibleMappings;
              return (
                <div
                  key={mapping.source}
                  style={{
                    display: "contents",
                  }}
                >
                  {/* Left: source */}
                  <div
                    ref={(el) => {
                      leftRefs.current[i] = el;
                    }}
                    className={visible ? "animate-fade-in" : ""}
                    style={{
                      opacity: visible ? 1 : 0,
                      transform: visible
                        ? "translateX(0)"
                        : "translateX(-10px)",
                      transition:
                        "opacity 0.4s ease-out, transform 0.4s ease-out",
                      background: "rgba(244,63,94,0.06)",
                      border: "1px solid rgba(244,63,94,0.2)",
                      borderRadius: 6,
                      padding: "0.5rem 0.7rem",
                      fontFamily: MONO,
                      fontSize: "0.8rem",
                      color: TEXT,
                      textAlign: "center",
                      position: "relative",
                      zIndex: 2,
                    }}
                  >
                    {mapping.source}
                  </div>

                  {/* Center: arrow */}
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      opacity: visible ? 1 : 0,
                      transition: "opacity 0.4s ease-out",
                      minWidth: 40,
                    }}
                  >
                    {mounted && (
                      <svg
                        width="32"
                        height="16"
                        viewBox="0 0 32 16"
                        fill="none"
                      >
                        <line
                          x1="2"
                          y1="8"
                          x2="24"
                          y2="8"
                          stroke={YELLOW_DIM}
                          strokeWidth="1.5"
                        />
                        <path
                          d="M20 4 L28 8 L20 12"
                          stroke={YELLOW}
                          strokeWidth="1.5"
                          fill="none"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                    )}
                  </div>

                  {/* Right: target */}
                  <div
                    ref={(el) => {
                      rightRefs.current[i] = el;
                    }}
                    className={visible ? "animate-fade-in" : ""}
                    style={{
                      opacity: visible ? 1 : 0,
                      transform: visible
                        ? "translateX(0)"
                        : "translateX(10px)",
                      transition:
                        "opacity 0.4s ease-out, transform 0.4s ease-out",
                      background: "rgba(250,204,21,0.06)",
                      border: "1px solid rgba(250,204,21,0.2)",
                      borderRadius: 6,
                      padding: "0.5rem 0.7rem",
                      fontFamily: MONO,
                      fontSize: "0.8rem",
                      color: TEXT,
                      textAlign: "center",
                      position: "relative",
                      zIndex: 2,
                    }}
                  >
                    {mapping.target}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ---- Placeholder when idle ---- */}
      {phase === "idle" && (
        <div
          className="rounded-lg flex items-center justify-center"
          style={{
            height: 100,
            border: "1px dashed rgba(255,255,255,0.1)",
            color: MUTED,
            fontFamily: MONO,
            fontSize: "0.78rem",
          }}
        >
          Press &ldquo;Find Analogies&rdquo; to begin
        </div>
      )}

      {/* ---- Completion insight ---- */}
      {phase === "done" && (
        <div
          className="animate-fade-in"
          style={{
            marginTop: "1.25rem",
            background: "rgba(250,204,21,0.05)",
            border: "1px solid rgba(250,204,21,0.2)",
            borderRadius: 10,
            padding: "0.85rem 1rem",
            boxShadow: "0 0 20px rgba(250,204,21,0.06)",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              marginBottom: "0.45rem",
            }}
          >
            {mounted && (
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <circle
                  cx="8"
                  cy="8"
                  r="6.5"
                  stroke={YELLOW}
                  strokeWidth="1.2"
                  fill="none"
                />
                <path
                  d="M5.5 8 L7 9.5 L10.5 6"
                  stroke={YELLOW}
                  strokeWidth="1.3"
                  fill="none"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            )}
            <span
              style={{
                fontFamily: MONO,
                fontSize: "0.68rem",
                textTransform: "uppercase",
                letterSpacing: "0.06em",
                color: YELLOW,
                fontWeight: 700,
              }}
            >
              Analogical Transfer Complete
            </span>
          </div>
          <p
            style={{
              color: "#b4b4bc",
              margin: 0,
              fontSize: "0.82rem",
              lineHeight: 1.7,
            }}
          >
            By mapping the circulatory system&apos;s structure onto the delivery
            problem, we derive a hub-and-spoke network with prioritized routing,
            adaptive capacity, and a central coordination point&mdash;mirroring
            how biology solved distribution at scale.
          </p>
        </div>
      )}

      {/* ---- Progress bar ---- */}
      <div className="mt-6 flex items-center gap-3">
        <span
          style={{
            fontFamily: MONO,
            fontSize: "0.7rem",
            color: MUTED,
          }}
        >
          {phase === "idle"
            ? "0/3"
            : phase === "structure"
            ? "1/3"
            : phase === "analogies"
            ? "2/3"
            : "3/3"}{" "}
          phases
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
              width:
                phase === "idle"
                  ? "0%"
                  : phase === "structure"
                  ? "33%"
                  : phase === "analogies"
                  ? "66%"
                  : "100%",
              height: "100%",
              borderRadius: 2,
              background:
                phase === "done" || phase === "transfer"
                  ? YELLOW
                  : YELLOW_DIM,
              transition: "width 0.4s ease-out",
            }}
          />
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Utility: hex color to "r,g,b" string                               */
/* ------------------------------------------------------------------ */

function hexToRgb(hex: string): string {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  if (!result) return "255,255,255";
  return `${parseInt(result[1], 16)},${parseInt(result[2], 16)},${parseInt(result[3], 16)}`;
}
