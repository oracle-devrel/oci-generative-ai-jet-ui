"use client";

import { useState, useCallback, useRef, useEffect } from "react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface QAPair {
  question: string;
  answer: string;
  insight: string;
}

interface Topic {
  id: string;
  title: string;
  prompt: string;
  pairs: QAPair[];
  synthesis: string;
}

/* ------------------------------------------------------------------ */
/*  Data                                                               */
/* ------------------------------------------------------------------ */

const TOPICS: Topic[] = [
  {
    id: "consciousness",
    title: "Consciousness",
    prompt: "What is consciousness?",
    pairs: [
      {
        question:
          "What distinguishes conscious experience from mere information processing?",
        answer:
          "Consciousness involves subjective experience (qualia) \u2014 there\u2019s \u2018something it is like\u2019 to be conscious, beyond just processing data.",
        insight: "Qualia as the differentiator",
      },
      {
        question:
          "Can subjective experience be measured or observed from the outside?",
        answer:
          "Not directly \u2014 this is the \u2018hard problem\u2019 of consciousness. We can measure neural correlates but cannot verify inner experience.",
        insight: "The hard problem of consciousness",
      },
      {
        question:
          "If consciousness can\u2019t be measured, how do we know other humans are conscious?",
        answer:
          "Through behavioral similarity and shared biology \u2014 we infer consciousness by analogy to our own experience.",
        insight: "Inference by analogy",
      },
      {
        question:
          "Does this inference-by-analogy extend to AI systems?",
        answer:
          "It\u2019s debatable \u2014 AI lacks biological substrates but can exhibit complex behavior. The question is whether substrate matters.",
        insight: "Substrate independence question",
      },
    ],
    synthesis:
      "Consciousness is fundamentally characterized by subjective experience (qualia) that resists external measurement \u2014 the hard problem. We rely on inference-by-analogy from our own experience to attribute consciousness to others, but extending this to AI exposes a deep unresolved question: does the biological substrate matter, or could consciousness emerge from any sufficiently complex information-processing system?",
  },
  {
    id: "free-will",
    title: "Free Will",
    prompt: "Do humans have free will?",
    pairs: [
      {
        question:
          "What do we mean when we say someone acts \u2018freely\u2019?",
        answer:
          "We typically mean they could have chosen otherwise \u2014 that their action wasn\u2019t fully determined by prior causes outside their control.",
        insight: "Alternative possibilities criterion",
      },
      {
        question:
          "If the brain operates by physical laws, can any decision truly be \u2018undetermined\u2019?",
        answer:
          "Neuroscience suggests decisions arise from neural processes governed by physics. Quantum indeterminacy exists but randomness isn\u2019t the same as freedom.",
        insight: "Determinism vs. randomness gap",
      },
      {
        question:
          "Could free will be compatible with determinism if we redefine what \u2018free\u2019 means?",
        answer:
          "Compatibilists argue yes \u2014 freedom means acting from your own desires without external coercion, even if those desires are determined.",
        insight: "Compatibilist redefinition",
      },
      {
        question:
          "Does this redefinition satisfy our intuitive sense of free will, or does it change the subject?",
        answer:
          "Critics say it\u2019s a semantic trick \u2014 our deep intuition demands ultimate origination, not just absence of coercion. The debate remains unresolved.",
        insight: "Intuition vs. redefinition tension",
      },
    ],
    synthesis:
      "The free will question reveals a tension between our intuitive sense of ultimate origination and the deterministic picture from neuroscience. Compatibilism offers a pragmatic resolution by redefining freedom as acting from internal desires, but critics argue this sidesteps the core question. The debate exposes how deeply our concepts of agency, responsibility, and selfhood depend on unresolved metaphysical commitments.",
  },
];

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const MONO = "var(--font-mono), monospace";

const TEAL = "#2dd4bf";
const TEAL_DIM = "rgba(45,212,191,0.12)";
const TEAL_BORDER = "rgba(45,212,191,0.3)";

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function SocraticWidget() {
  /* --- Hydration guard -------------------------------------------- */
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  /* --- State ------------------------------------------------------ */
  const [topicIdx, setTopicIdx] = useState(0);
  const [phase, setPhase] = useState<"idle" | "running" | "done">("idle");
  const [visiblePairs, setVisiblePairs] = useState(0); // how many Q&A pairs are revealed
  const [showSynthesis, setShowSynthesis] = useState(false);
  // Track which sub-element is visible within the current pair:
  // 0 = nothing extra, 1 = answer visible, 2 = insight visible
  const [currentPairStep, setCurrentPairStep] = useState(0);

  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);
  const containerRef = useRef<HTMLDivElement>(null);

  const topic = TOPICS[topicIdx];
  const totalPairs = topic.pairs.length;

  /* --- Timer cleanup --------------------------------------------- */
  const clearTimers = useCallback(() => {
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];
  }, []);

  useEffect(() => clearTimers, [clearTimers]);

  /* --- Auto-scroll to bottom ------------------------------------- */
  const scrollToBottom = useCallback(() => {
    if (containerRef.current) {
      const el = containerRef.current;
      el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    }
  }, []);

  /* --- Reset ----------------------------------------------------- */
  const reset = useCallback(() => {
    clearTimers();
    setPhase("idle");
    setVisiblePairs(0);
    setCurrentPairStep(0);
    setShowSynthesis(false);
  }, [clearTimers]);

  /* --- Start questioning ----------------------------------------- */
  const startQuestioning = useCallback(() => {
    reset();
    setPhase("running");

    let delay = 300;

    for (let i = 0; i < topic.pairs.length; i++) {
      // Show question (visiblePairs increments to reveal next Q)
      const qDelay = delay;
      const t1 = setTimeout(() => {
        setVisiblePairs(i + 1);
        setCurrentPairStep(0);
        setTimeout(scrollToBottom, 50);
      }, qDelay);
      timersRef.current.push(t1);
      delay += 600;

      // Show answer
      const aDelay = delay;
      const t2 = setTimeout(() => {
        setCurrentPairStep(1);
        setTimeout(scrollToBottom, 50);
      }, aDelay);
      timersRef.current.push(t2);
      delay += 600;

      // Show insight badge
      const iDelay = delay;
      const t3 = setTimeout(() => {
        setCurrentPairStep(2);
        setTimeout(scrollToBottom, 50);
      }, iDelay);
      timersRef.current.push(t3);
      delay += 400;
    }

    // Show synthesis
    const synthDelay = delay;
    const t4 = setTimeout(() => {
      setShowSynthesis(true);
      setPhase("done");
      setTimeout(scrollToBottom, 50);
    }, synthDelay);
    timersRef.current.push(t4);
  }, [topic, reset, scrollToBottom]);

  /* --- Topic switch ---------------------------------------------- */
  const handleTopicSwitch = useCallback(
    (idx: number) => {
      if (idx === topicIdx) return;
      reset();
      setTopicIdx(idx);
    },
    [topicIdx, reset],
  );

  /* --- Derive visibility ----------------------------------------- */
  // For a given pair index, determine what parts are visible
  function pairVisibility(pairIdx: number): {
    questionVisible: boolean;
    answerVisible: boolean;
    insightVisible: boolean;
  } {
    if (pairIdx + 1 < visiblePairs) {
      // Fully completed pair
      return { questionVisible: true, answerVisible: true, insightVisible: true };
    }
    if (pairIdx + 1 === visiblePairs) {
      // Currently revealing pair
      return {
        questionVisible: true,
        answerVisible: currentPairStep >= 1,
        insightVisible: currentPairStep >= 2,
      };
    }
    return { questionVisible: false, answerVisible: false, insightVisible: false };
  }

  /* --- Current question counter ---------------------------------- */
  const displayedQuestion = Math.min(visiblePairs, totalPairs);

  /* ---------------------------------------------------------------- */
  /*  Render                                                           */
  /* ---------------------------------------------------------------- */

  if (!mounted) {
    return (
      <div className="widget-container s6">
        <div className="widget-label">Interactive &middot; Socratic Method</div>
        <div style={{ minHeight: 300 }} />
      </div>
    );
  }

  return (
    <div className="widget-container s6">
      <div className="widget-label">Interactive &middot; Socratic Method</div>

      {/* ---- Topic selector ---- */}
      <div className="flex flex-wrap items-center gap-2 mb-4">
        {TOPICS.map((t, i) => (
          <button
            key={t.id}
            onClick={() => handleTopicSwitch(i)}
            className={`btn-mono ${i === topicIdx ? "active" : ""}`}
          >
            {t.title}
          </button>
        ))}
      </div>

      {/* ---- Topic prompt ---- */}
      <div
        className="rounded-lg p-4 mb-5"
        style={{
          background: "rgba(45,212,191,0.04)",
          border: `1px solid ${TEAL_BORDER}`,
        }}
      >
        <span
          style={{
            fontFamily: MONO,
            fontSize: "0.7rem",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            color: TEAL,
            fontWeight: 600,
            display: "block",
            marginBottom: 4,
          }}
        >
          Topic
        </span>
        <p style={{ color: "#e4e4e7", margin: 0, lineHeight: 1.7, fontSize: "0.95rem" }}>
          {topic.prompt}
        </p>
      </div>

      {/* ---- Controls ---- */}
      <div className="flex flex-wrap items-center gap-3 mb-6">
        <button
          className="btn-mono"
          onClick={startQuestioning}
          disabled={phase === "running"}
          style={{
            background: phase === "running" ? "transparent" : TEAL_DIM,
            borderColor: phase === "running" ? "rgba(255,255,255,0.08)" : TEAL_BORDER,
            color: phase === "running" ? "#a1a1aa" : TEAL,
            cursor: phase === "running" ? "not-allowed" : "pointer",
          }}
        >
          {phase === "running" ? "Questioning\u2026" : "Begin Questioning"}
        </button>

        <button className="btn-mono" onClick={reset}>
          Reset
        </button>

        {phase !== "idle" && (
          <span
            style={{
              fontFamily: MONO,
              fontSize: "0.75rem",
              color: "#a1a1aa",
              background: "rgba(255,255,255,0.05)",
              borderRadius: 4,
              padding: "0.2rem 0.55rem",
            }}
          >
            Question {displayedQuestion}/{totalPairs}
          </span>
        )}
      </div>

      {/* ---- Conversation area ---- */}
      <div
        ref={containerRef}
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "0.75rem",
          maxHeight: 520,
          overflowY: "auto",
          paddingRight: 4,
        }}
      >
        {/* Placeholder when idle */}
        {phase === "idle" && visiblePairs === 0 && (
          <div
            className="rounded-lg flex items-center justify-center"
            style={{
              height: 100,
              border: "1px dashed rgba(255,255,255,0.1)",
              color: "#a1a1aa",
              fontFamily: MONO,
              fontSize: "0.78rem",
            }}
          >
            Press &ldquo;Begin Questioning&rdquo; to start the Socratic dialogue
          </div>
        )}

        {/* Q&A pairs */}
        {topic.pairs.map((pair, idx) => {
          const vis = pairVisibility(idx);
          if (!vis.questionVisible) return null;

          // Alternate indent: even questions indent 0, odd indent slightly
          const indent = idx % 2 === 1 ? 12 : 0;

          return (
            <div
              key={`${topic.id}-pair-${idx}`}
              className="animate-slide-in"
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "0.5rem",
                marginLeft: indent,
              }}
            >
              {/* Question */}
              <div
                style={{
                  background: "rgba(45,212,191,0.03)",
                  borderLeft: `3px solid ${TEAL}`,
                  borderRadius: "0 8px 8px 0",
                  padding: "0.7rem 0.85rem",
                  display: "flex",
                  gap: "0.65rem",
                  alignItems: "flex-start",
                }}
              >
                {/* Q badge */}
                <span
                  style={{
                    fontFamily: MONO,
                    fontSize: "0.6rem",
                    fontWeight: 700,
                    color: "#12131a",
                    background: TEAL,
                    borderRadius: 4,
                    padding: "2px 7px",
                    flexShrink: 0,
                    marginTop: 2,
                    letterSpacing: "0.04em",
                  }}
                >
                  Q
                </span>
                <p
                  style={{
                    color: TEAL,
                    margin: 0,
                    fontSize: "0.88rem",
                    lineHeight: 1.65,
                    fontWeight: 500,
                  }}
                >
                  {pair.question}
                </p>
              </div>

              {/* Answer */}
              {vis.answerVisible && (
                <div
                  className="animate-fade-in"
                  style={{
                    background: "rgba(255,255,255,0.03)",
                    border: "1px solid rgba(255,255,255,0.06)",
                    borderRadius: 8,
                    padding: "0.7rem 0.85rem",
                    marginLeft: 8,
                    display: "flex",
                    gap: "0.65rem",
                    alignItems: "flex-start",
                  }}
                >
                  {/* A badge */}
                  <span
                    style={{
                      fontFamily: MONO,
                      fontSize: "0.6rem",
                      fontWeight: 700,
                      color: "#12131a",
                      background: "#a1a1aa",
                      borderRadius: 4,
                      padding: "2px 7px",
                      flexShrink: 0,
                      marginTop: 2,
                      letterSpacing: "0.04em",
                    }}
                  >
                    A
                  </span>
                  <p
                    style={{
                      color: "#d4d4d8",
                      margin: 0,
                      fontSize: "0.84rem",
                      lineHeight: 1.65,
                    }}
                  >
                    {pair.answer}
                  </p>
                </div>
              )}

              {/* Insight badge */}
              {vis.insightVisible && (
                <div
                  className="animate-fade-in"
                  style={{
                    marginLeft: 8,
                    display: "flex",
                    alignItems: "center",
                    gap: "0.45rem",
                  }}
                >
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                    <circle cx="6" cy="6" r="5" stroke={TEAL} strokeWidth="1" fill="none" />
                    <path
                      d="M4 6 L5.5 7.5 L8 4.5"
                      stroke={TEAL}
                      strokeWidth="1"
                      fill="none"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                  <span
                    style={{
                      fontFamily: MONO,
                      fontSize: "0.62rem",
                      fontWeight: 600,
                      letterSpacing: "0.06em",
                      textTransform: "uppercase",
                      color: TEAL,
                      background: TEAL_DIM,
                      padding: "2px 10px",
                      borderRadius: 999,
                    }}
                  >
                    Insight extracted: {pair.insight}
                  </span>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* ---- Synthesis panel ---- */}
      {showSynthesis && (
        <div
          className="animate-fade-in"
          style={{
            marginTop: "1.25rem",
            background: "rgba(45,212,191,0.05)",
            border: `1px solid ${TEAL_BORDER}`,
            borderRadius: 10,
            padding: "1rem 1.15rem",
            boxShadow: "0 0 24px rgba(45,212,191,0.08)",
          }}
        >
          {/* Synthesis header */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.6rem",
              marginBottom: "0.65rem",
            }}
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path
                d="M8 1 L9.5 5.5 L14 6 L10.5 9.5 L11.5 14 L8 11.5 L4.5 14 L5.5 9.5 L2 6 L6.5 5.5 Z"
                stroke={TEAL}
                strokeWidth="1"
                fill="rgba(45,212,191,0.15)"
                strokeLinejoin="round"
              />
            </svg>
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
              Synthesis
            </span>
          </div>

          {/* Insight summary pills */}
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: "0.4rem",
              marginBottom: "0.75rem",
            }}
          >
            {topic.pairs.map((pair, i) => (
              <span
                key={`synth-insight-${i}`}
                style={{
                  fontFamily: MONO,
                  fontSize: "0.58rem",
                  fontWeight: 600,
                  letterSpacing: "0.04em",
                  color: TEAL,
                  background: TEAL_DIM,
                  border: `1px solid rgba(45,212,191,0.18)`,
                  padding: "2px 8px",
                  borderRadius: 999,
                }}
              >
                {pair.insight}
              </span>
            ))}
          </div>

          {/* Synthesized conclusion */}
          <p
            style={{
              color: "#d4d4d8",
              margin: 0,
              fontSize: "0.84rem",
              lineHeight: 1.75,
            }}
          >
            {topic.synthesis}
          </p>
        </div>
      )}

      {/* ---- Progress bar ---- */}
      <div className="mt-6 flex items-center gap-3">
        <span
          style={{
            fontFamily: MONO,
            fontSize: "0.7rem",
            color: "#a1a1aa",
          }}
        >
          {displayedQuestion}/{totalPairs} questions
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
              width: `${(displayedQuestion / totalPairs) * 100}%`,
              height: "100%",
              borderRadius: 2,
              background:
                showSynthesis
                  ? TEAL
                  : "rgba(45,212,191,0.5)",
              transition: "width 0.35s ease-out",
            }}
          />
        </div>
      </div>
    </div>
  );
}
