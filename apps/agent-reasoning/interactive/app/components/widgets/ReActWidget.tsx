"use client";

import { useState, useCallback, useRef, useEffect } from "react";

/* ------------------------------------------------------------------ */
/*  Types                                                             */
/* ------------------------------------------------------------------ */

type StepType = "thought" | "action" | "observation" | "answer";

interface Step {
  type: StepType;
  content: string;
  tool?: string;
  toolInput?: string;
}

interface Example {
  id: string;
  query: string;
  tools: string[];
  steps: Step[];
}

/* ------------------------------------------------------------------ */
/*  Data                                                              */
/* ------------------------------------------------------------------ */

const EXAMPLES: Example[] = [
  {
    id: "capital-pop",
    query: "What is the population of the capital of France?",
    tools: ["web_search", "calculate", "search"],
    steps: [
      {
        type: "thought",
        content:
          "I need to find the capital of France first, then look up its population.",
      },
      {
        type: "action",
        content: 'search["capital of France"]',
        tool: "search",
        toolInput: "capital of France",
      },
      {
        type: "observation",
        content: "The capital of France is Paris.",
      },
      {
        type: "thought",
        content: "Now I need to find the population of Paris.",
      },
      {
        type: "action",
        content: 'web_search["population of Paris 2024"]',
        tool: "web_search",
        toolInput: "population of Paris 2024",
      },
      {
        type: "observation",
        content: "The population of Paris is approximately 2.16 million.",
      },
      {
        type: "thought",
        content: "I now have enough information to answer.",
      },
      {
        type: "answer",
        content:
          "The population of the capital of France (Paris) is approximately 2.16 million.",
      },
    ],
  },
  {
    id: "tallest-mountain",
    query: "How tall is the tallest mountain in Japan in feet?",
    tools: ["web_search", "calculate", "search"],
    steps: [
      {
        type: "thought",
        content:
          "I need to find the tallest mountain in Japan, get its height, then convert to feet.",
      },
      {
        type: "action",
        content: 'search["tallest mountain in Japan"]',
        tool: "search",
        toolInput: "tallest mountain in Japan",
      },
      {
        type: "observation",
        content:
          "Mount Fuji is the tallest mountain in Japan at 3,776 meters.",
      },
      {
        type: "thought",
        content:
          "I have the height in meters. I need to convert 3,776 meters to feet.",
      },
      {
        type: "action",
        content: 'calculate["3776 * 3.28084"]',
        tool: "calculate",
        toolInput: "3776 * 3.28084",
      },
      {
        type: "observation",
        content: "12,388.45 feet",
      },
      {
        type: "thought",
        content:
          "I now have the height in feet. I can provide the final answer.",
      },
      {
        type: "answer",
        content:
          "The tallest mountain in Japan is Mount Fuji, standing at approximately 12,388 feet (3,776 meters).",
      },
    ],
  },
  {
    id: "gdp-comparison",
    query: "Is the GDP of Brazil larger than Canada's?",
    tools: ["web_search", "calculate", "search"],
    steps: [
      {
        type: "thought",
        content:
          "I need to look up the GDP of both Brazil and Canada, then compare them.",
      },
      {
        type: "action",
        content: 'web_search["GDP of Brazil 2024"]',
        tool: "web_search",
        toolInput: "GDP of Brazil 2024",
      },
      {
        type: "observation",
        content: "Brazil's GDP in 2024 is approximately $2.13 trillion (nominal).",
      },
      {
        type: "action",
        content: 'web_search["GDP of Canada 2024"]',
        tool: "web_search",
        toolInput: "GDP of Canada 2024",
      },
      {
        type: "observation",
        content:
          "Canada's GDP in 2024 is approximately $2.14 trillion (nominal).",
      },
      {
        type: "thought",
        content:
          "The two GDPs are very close. Brazil at ~$2.13T vs Canada at ~$2.14T. Canada's is slightly larger.",
      },
      {
        type: "answer",
        content:
          "No. Brazil's GDP (~$2.13T) is slightly smaller than Canada's (~$2.14T), though they are very close in size.",
      },
    ],
  },
];

/* ------------------------------------------------------------------ */
/*  Color palette per step type                                       */
/* ------------------------------------------------------------------ */

const TYPE_META: Record<
  StepType,
  { label: string; color: string; bg: string; swimlane: string }
> = {
  thought: {
    label: "THOUGHT",
    color: "#22d3ee",
    bg: "rgba(34,211,238,0.12)",
    swimlane: "swimlane-thought",
  },
  action: {
    label: "ACTION",
    color: "#f97316",
    bg: "rgba(249,115,22,0.12)",
    swimlane: "swimlane-action",
  },
  observation: {
    label: "OBSERVATION",
    color: "#4ade80",
    bg: "rgba(74,222,128,0.12)",
    swimlane: "swimlane-observation",
  },
  answer: {
    label: "FINAL ANSWER",
    color: "#a78bfa",
    bg: "rgba(167,139,250,0.12)",
    swimlane: "",
  },
};

/* ------------------------------------------------------------------ */
/*  Widget                                                            */
/* ------------------------------------------------------------------ */

export function ReActWidget() {
  const [exampleIdx, setExampleIdx] = useState(0);
  const [visibleCount, setVisibleCount] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const example = EXAMPLES[exampleIdx];
  const totalSteps = example.steps.length;

  /* ---- cleanup on unmount ---- */
  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  /* ---- auto-scroll when new step appears ---- */
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [visibleCount]);

  /* ---- step-through timer ---- */
  const advanceStep = useCallback(() => {
    setVisibleCount((prev) => {
      const next = prev + 1;
      if (next >= totalSteps) {
        setIsPlaying(false);
        return totalSteps;
      }
      return next;
    });
  }, [totalSteps]);

  useEffect(() => {
    if (isPlaying && visibleCount < totalSteps) {
      timerRef.current = setTimeout(advanceStep, 600);
    }
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [isPlaying, visibleCount, totalSteps, advanceStep]);

  /* ---- handlers ---- */
  const handleRun = useCallback(() => {
    setVisibleCount(0);
    setIsPlaying(true);
    // kick off first step after a micro-delay so count resets
    setTimeout(() => setVisibleCount(1), 50);
  }, []);

  const handleReset = useCallback(() => {
    setIsPlaying(false);
    if (timerRef.current) clearTimeout(timerRef.current);
    setVisibleCount(0);
  }, []);

  const handleAutoPlay = useCallback(() => {
    if (isPlaying) {
      setIsPlaying(false);
      if (timerRef.current) clearTimeout(timerRef.current);
    } else {
      if (visibleCount >= totalSteps) {
        setVisibleCount(0);
        setTimeout(() => {
          setVisibleCount(1);
          setIsPlaying(true);
        }, 50);
      } else if (visibleCount === 0) {
        setVisibleCount(1);
        setIsPlaying(true);
      } else {
        setIsPlaying(true);
      }
    }
  }, [isPlaying, visibleCount, totalSteps]);

  const switchExample = useCallback(
    (idx: number) => {
      if (idx === exampleIdx) return;
      setIsPlaying(false);
      if (timerRef.current) clearTimeout(timerRef.current);
      setExampleIdx(idx);
      setVisibleCount(0);
    },
    [exampleIdx],
  );

  /* ---- render helpers ---- */
  const renderToolBadges = () => (
    <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
      <span
        style={{
          fontFamily: "var(--font-mono, monospace)",
          fontSize: "0.7rem",
          color: "#a1a1aa",
          marginRight: "0.25rem",
          alignSelf: "center",
        }}
      >
        Tools:
      </span>
      {example.tools.map((t) => (
        <span
          key={t}
          style={{
            fontFamily: "var(--font-mono, monospace)",
            fontSize: "0.7rem",
            padding: "0.2rem 0.55rem",
            borderRadius: "9999px",
            background: "rgba(249,115,22,0.12)",
            color: "#f97316",
            border: "1px solid rgba(249,115,22,0.25)",
          }}
        >
          {t}
        </span>
      ))}
    </div>
  );

  const renderStepCard = (step: Step, index: number) => {
    const meta = TYPE_META[step.type];
    const isAnswer = step.type === "answer";

    return (
      <div
        key={index}
        className={`animate-slide-in ${isAnswer ? "" : meta.swimlane}`}
        style={{
          background: "rgba(255,255,255,0.02)",
          borderRadius: "8px",
          padding: "0.75rem 1rem",
          animationDelay: `${index * 0.05}s`,
          ...(isAnswer
            ? {
                borderLeft: "3px solid #a78bfa",
                boxShadow:
                  "0 0 12px rgba(167,139,250,0.15), 0 0 4px rgba(167,139,250,0.1)",
              }
            : {}),
        }}
      >
        {/* type badge */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            marginBottom: "0.4rem",
          }}
        >
          <span
            style={{
              fontFamily: "var(--font-mono, monospace)",
              fontSize: "0.6rem",
              fontWeight: 700,
              letterSpacing: "0.08em",
              padding: "0.15rem 0.5rem",
              borderRadius: "4px",
              background: meta.bg,
              color: meta.color,
            }}
          >
            {meta.label}
          </span>
          {step.tool && (
            <span
              style={{
                fontFamily: "var(--font-mono, monospace)",
                fontSize: "0.6rem",
                padding: "0.15rem 0.5rem",
                borderRadius: "4px",
                background: "rgba(249,115,22,0.18)",
                color: "#fb923c",
              }}
            >
              {step.tool}
            </span>
          )}
        </div>

        {/* content */}
        {step.type === "action" ? (
          <div
            style={{
              fontFamily: "var(--font-mono, monospace)",
              fontSize: "0.82rem",
              color: "#e4e4e7",
              lineHeight: 1.5,
            }}
          >
            <span style={{ color: "#a1a1aa" }}>Action: </span>
            <span style={{ color: "#f97316" }}>{step.tool}</span>
            <span style={{ color: "#a1a1aa" }}>[</span>
            <span style={{ color: "#e4e4e7" }}>
              &quot;{step.toolInput}&quot;
            </span>
            <span style={{ color: "#a1a1aa" }}>]</span>
          </div>
        ) : (
          <p
            style={{
              fontSize: "0.85rem",
              color: isAnswer ? "#e4e4e7" : "#b4b4bc",
              lineHeight: 1.6,
              margin: 0,
              ...(isAnswer ? { fontWeight: 500 } : {}),
            }}
          >
            {step.content}
          </p>
        )}
      </div>
    );
  };

  return (
    <div className="widget-container s2">
      <div className="widget-label">
        Interactive &middot; ReAct (Reason + Act)
      </div>

      {/* ---- Query selector tabs ---- */}
      <div
        style={{
          display: "flex",
          gap: "0.4rem",
          flexWrap: "wrap",
          marginBottom: "1rem",
        }}
      >
        {EXAMPLES.map((ex, i) => (
          <button
            key={ex.id}
            className={`btn-mono${i === exampleIdx ? " active" : ""}`}
            onClick={() => switchExample(i)}
          >
            {ex.query.length > 36
              ? ex.query.slice(0, 33) + "..."
              : ex.query}
          </button>
        ))}
      </div>

      {/* ---- Query display ---- */}
      <div
        style={{
          fontFamily: "var(--font-mono, monospace)",
          fontSize: "0.85rem",
          color: "#e4e4e7",
          background: "rgba(0,0,0,0.4)",
          border: "1px solid rgba(255,255,255,0.08)",
          borderRadius: "8px",
          padding: "0.75rem 1rem",
          marginBottom: "1rem",
        }}
      >
        <span style={{ color: "#a1a1aa" }}>Query: </span>
        {example.query}
      </div>

      {/* ---- Tool badges ---- */}
      <div style={{ marginBottom: "1rem" }}>{renderToolBadges()}</div>

      {/* ---- Controls row ---- */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0.5rem",
          marginBottom: "1rem",
          flexWrap: "wrap",
        }}
      >
        <button className="btn-mono" onClick={handleRun}>
          Run ReAct
        </button>
        <button className="btn-mono" onClick={handleAutoPlay}>
          {isPlaying ? "Pause" : "Auto Play"}
        </button>
        <button className="btn-mono" onClick={handleReset}>
          Reset
        </button>

        {/* step counter */}
        <span
          style={{
            fontFamily: "var(--font-mono, monospace)",
            fontSize: "0.72rem",
            color: "#a1a1aa",
            marginLeft: "auto",
          }}
        >
          Step {Math.min(visibleCount, totalSteps)}/{totalSteps}
        </span>
      </div>

      {/* ---- Progress bar ---- */}
      <div
        style={{
          height: "3px",
          background: "rgba(255,255,255,0.06)",
          borderRadius: "2px",
          marginBottom: "1rem",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${(visibleCount / totalSteps) * 100}%`,
            background: "linear-gradient(90deg, #22d3ee, #4ade80)",
            borderRadius: "2px",
            transition: "width 0.4s ease-out",
          }}
        />
      </div>

      {/* ---- Swimlane / timeline ---- */}
      <div
        ref={scrollRef}
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "0.5rem",
          maxHeight: "420px",
          overflowY: "auto",
          paddingRight: "0.25rem",
          minHeight: "80px",
        }}
        className="scrollbar-hide"
      >
        {visibleCount === 0 && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              height: "80px",
              color: "#a1a1aa",
              fontFamily: "var(--font-mono, monospace)",
              fontSize: "0.78rem",
            }}
          >
            Press &quot;Run ReAct&quot; to begin
          </div>
        )}
        {example.steps.slice(0, visibleCount).map((step, i) =>
          renderStepCard(step, i),
        )}
      </div>

      {/* ---- Loop legend ---- */}
      <div
        style={{
          display: "flex",
          gap: "1rem",
          marginTop: "1rem",
          flexWrap: "wrap",
        }}
      >
        {(["thought", "action", "observation"] as StepType[]).map((t) => (
          <div
            key={t}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.35rem",
            }}
          >
            <span
              style={{
                width: "10px",
                height: "10px",
                borderRadius: "2px",
                background: TYPE_META[t].color,
                display: "inline-block",
                flexShrink: 0,
              }}
            />
            <span
              style={{
                fontFamily: "var(--font-mono, monospace)",
                fontSize: "0.65rem",
                color: "#a1a1aa",
                textTransform: "capitalize",
              }}
            >
              {t}
            </span>
          </div>
        ))}
        <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
          <span
            style={{
              width: "10px",
              height: "10px",
              borderRadius: "2px",
              background: "#a78bfa",
              display: "inline-block",
              flexShrink: 0,
            }}
          />
          <span
            style={{
              fontFamily: "var(--font-mono, monospace)",
              fontSize: "0.65rem",
              color: "#a1a1aa",
            }}
          >
            Final answer
          </span>
        </div>
      </div>
    </div>
  );
}
