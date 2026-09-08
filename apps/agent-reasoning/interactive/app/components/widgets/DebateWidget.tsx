"use client";

import { useState, useCallback, useRef, useEffect } from "react";

/* ------------------------------------------------------------------ */
/*  Data                                                               */
/* ------------------------------------------------------------------ */

interface Argument {
  side: "pro" | "con";
  text: string;
}

interface JudgeScore {
  pro: number;
  con: number;
  reasoning: string;
}

interface Round {
  pro: string;
  con: string;
  judge: JudgeScore;
}

interface Topic {
  id: string;
  title: string;
  question: string;
  rounds: Round[];
  verdict: string;
  synthesis: string;
}

const TOPICS: Topic[] = [
  {
    id: "legal-personhood",
    title: "AI Legal Personhood",
    question: "Should AI systems be given legal personhood?",
    rounds: [
      {
        pro: "AI systems can make autonomous decisions, own property, and bear responsibility. Legal personhood provides a framework for accountability.",
        con: "Personhood implies consciousness and moral agency. AI lacks subjective experience and genuine understanding.",
        judge: { pro: 6.5, con: 7.2, reasoning: "CON\u2019s philosophical argument is more foundational" },
      },
      {
        pro: "Legal fictions already exist\u2014corporations have personhood without consciousness. This is about practical governance.",
        con: "Corporate personhood is already controversial. Extending it to AI could dilute human rights and create perverse incentives.",
        judge: { pro: 7.8, con: 7.0, reasoning: "PRO\u2019s corporate analogy is compelling" },
      },
      {
        pro: "Without legal status, who is responsible when an autonomous AI causes harm? Personhood solves the liability gap.",
        con: "Strict liability for manufacturers and operators already addresses this. New legal categories aren\u2019t needed\u2014better enforcement is.",
        judge: { pro: 7.5, con: 7.8, reasoning: "CON provides a practical alternative" },
      },
    ],
    verdict: "CON wins 22.0 to 21.8",
    synthesis:
      "While PRO raises valid governance concerns, CON demonstrates that existing legal frameworks can address AI accountability without the philosophical and practical risks of granting personhood.",
  },
  {
    id: "open-source",
    title: "Open-Source AI Models",
    question: "Should frontier AI models be required to be open-source?",
    rounds: [
      {
        pro: "Open-source accelerates research, enables auditing, and prevents monopolistic control over a transformative technology.",
        con: "Unrestricted access to powerful models enables misuse\u2014deepfakes, bioweapons research, and large-scale manipulation.",
        judge: { pro: 7.0, con: 7.5, reasoning: "CON\u2019s safety risks are concrete and immediate" },
      },
      {
        pro: "Closed models aren\u2019t safer\u2014they just hide risks. Open review produces more robust safety through collective scrutiny.",
        con: "Security through obscurity isn\u2019t the argument. It\u2019s about controlling proliferation of capabilities beyond defensive capacity.",
        judge: { pro: 7.3, con: 6.8, reasoning: "PRO effectively reframes the transparency debate" },
      },
      {
        pro: "History shows open ecosystems win: Linux, the web, TCP/IP. Closed AI will fragment into incompatible silos.",
        con: "Nuclear technology and gain-of-function research show that some capabilities require gatekeeping, regardless of ecosystem benefits.",
        judge: { pro: 6.9, con: 7.6, reasoning: "CON\u2019s dual-use analogy is stronger" },
      },
    ],
    verdict: "CON wins 21.9 to 21.2",
    synthesis:
      "PRO makes strong arguments about innovation and oversight, but CON persuasively argues that frontier capabilities require nuanced access controls beyond full open-source release.",
  },
];

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const MONO = "var(--font-mono), monospace";

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
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function DebateWidget() {
  /* --- Hydration guard -------------------------------------------- */
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  /* --- State ------------------------------------------------------ */
  const [topicIdx, setTopicIdx] = useState(0);
  const [phase, setPhase] = useState<"idle" | "running" | "done">("idle");
  const [currentRound, setCurrentRound] = useState(0); // 0-based index of round being animated
  const [visibleArgs, setVisibleArgs] = useState<Argument[]>([]); // arguments revealed so far
  const [judgedRounds, setJudgedRounds] = useState<number>(0); // how many rounds have been scored
  const [showVerdict, setShowVerdict] = useState(false);

  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  const topic = TOPICS[topicIdx];
  const totalRounds = topic.rounds.length;

  /* --- Timers cleanup -------------------------------------------- */
  const clearTimers = useCallback(() => {
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];
  }, []);

  useEffect(() => clearTimers, [clearTimers]);

  /* --- Running score -------------------------------------------- */
  const runningPro = topic.rounds
    .slice(0, judgedRounds)
    .reduce((sum, r) => sum + r.judge.pro, 0);
  const runningCon = topic.rounds
    .slice(0, judgedRounds)
    .reduce((sum, r) => sum + r.judge.con, 0);

  /* --- Reset ----------------------------------------------------- */
  const reset = useCallback(() => {
    clearTimers();
    setPhase("idle");
    setCurrentRound(0);
    setVisibleArgs([]);
    setJudgedRounds(0);
    setShowVerdict(false);
  }, [clearTimers]);

  /* --- Start debate ---------------------------------------------- */
  const startDebate = useCallback(() => {
    reset();
    setPhase("running");

    let delay = 400;

    topic.rounds.forEach((round, rIdx) => {
      // Show PRO argument
      const proDelay = delay;
      const t1 = setTimeout(() => {
        setCurrentRound(rIdx);
        setVisibleArgs((prev) => [...prev, { side: "pro", text: round.pro }]);
      }, proDelay);
      timersRef.current.push(t1);
      delay += 1000;

      // Show CON argument
      const conDelay = delay;
      const t2 = setTimeout(() => {
        setVisibleArgs((prev) => [...prev, { side: "con", text: round.con }]);
      }, conDelay);
      timersRef.current.push(t2);
      delay += 1000;

      // Show judge score
      const judgeDelay = delay;
      const t3 = setTimeout(() => {
        setJudgedRounds(rIdx + 1);
      }, judgeDelay);
      timersRef.current.push(t3);
      delay += 800;
    });

    // Show final verdict
    const verdictDelay = delay;
    const t4 = setTimeout(() => {
      setShowVerdict(true);
      setPhase("done");
    }, verdictDelay);
    timersRef.current.push(t4);
  }, [topic, reset]);

  /* --- Topic switch ---------------------------------------------- */
  const handleTopicSwitch = useCallback(
    (idx: number) => {
      if (idx === topicIdx) return;
      reset();
      setTopicIdx(idx);
    },
    [topicIdx, reset],
  );

  /* --- Derive visible data per round ----------------------------- */
  // Group visible arguments into rounds
  const roundsData: { pro?: string; con?: string; judged: boolean; judge: JudgeScore }[] = [];
  let argIdx = 0;
  for (let r = 0; r < totalRounds; r++) {
    const entry: { pro?: string; con?: string; judged: boolean; judge: JudgeScore } = {
      judged: r < judgedRounds,
      judge: topic.rounds[r].judge,
    };
    if (argIdx < visibleArgs.length && visibleArgs[argIdx].side === "pro") {
      entry.pro = visibleArgs[argIdx].text;
      argIdx++;
    }
    if (argIdx < visibleArgs.length && visibleArgs[argIdx].side === "con") {
      entry.con = visibleArgs[argIdx].text;
      argIdx++;
    }
    if (entry.pro || entry.con) {
      roundsData.push(entry);
    }
  }

  /* ---------------------------------------------------------------- */
  /*  Render                                                           */
  /* ---------------------------------------------------------------- */

  return (
    <div className="widget-container s6">
      <div className="widget-label">Interactive &middot; Adversarial Debate</div>

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

      {/* ---- Topic question ---- */}
      <div
        className="rounded-lg p-4 mb-5"
        style={{
          background: "rgba(255,255,255,0.03)",
          border: "1px solid rgba(255,255,255,0.08)",
        }}
      >
        <span style={monoLabel("#a1a1aa")} className="block mb-1">
          Topic
        </span>
        <p style={{ color: "#e4e4e7", margin: 0, lineHeight: 1.7, fontSize: "0.95rem" }}>
          {topic.question}
        </p>
      </div>

      {/* ---- Running scoreboard ---- */}
      {judgedRounds > 0 && (
        <div
          className="animate-fade-in mb-5"
          style={{
            display: "flex",
            alignItems: "center",
            gap: "1.25rem",
            background: "rgba(0,0,0,0.35)",
            border: "1px solid rgba(255,255,255,0.06)",
            borderRadius: 8,
            padding: "0.65rem 1rem",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span
              style={{
                width: 10,
                height: 10,
                borderRadius: "50%",
                background: "#4ade80",
                flexShrink: 0,
              }}
            />
            <span style={{ fontFamily: MONO, fontSize: "0.75rem", color: "#4ade80", fontWeight: 600 }}>
              PRO
            </span>
            <span style={{ fontFamily: MONO, fontSize: "1rem", color: "#4ade80", fontWeight: 700 }}>
              {runningPro.toFixed(1)}
            </span>
          </div>

          <div
            style={{
              flex: 1,
              height: 6,
              borderRadius: 3,
              background: "rgba(255,255,255,0.06)",
              overflow: "hidden",
              display: "flex",
            }}
          >
            {(runningPro + runningCon) > 0 && (
              <>
                <div
                  style={{
                    width: `${(runningPro / (runningPro + runningCon)) * 100}%`,
                    height: "100%",
                    background: "linear-gradient(90deg, #4ade80, rgba(74,222,128,0.4))",
                    transition: "width 0.5s ease-out",
                  }}
                />
                <div
                  style={{
                    width: `${(runningCon / (runningPro + runningCon)) * 100}%`,
                    height: "100%",
                    background: "linear-gradient(90deg, rgba(244,63,94,0.4), #f43f5e)",
                    transition: "width 0.5s ease-out",
                  }}
                />
              </>
            )}
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span style={{ fontFamily: MONO, fontSize: "1rem", color: "#f43f5e", fontWeight: 700 }}>
              {runningCon.toFixed(1)}
            </span>
            <span style={{ fontFamily: MONO, fontSize: "0.75rem", color: "#f43f5e", fontWeight: 600 }}>
              CON
            </span>
            <span
              style={{
                width: 10,
                height: 10,
                borderRadius: "50%",
                background: "#f43f5e",
                flexShrink: 0,
              }}
            />
          </div>
        </div>
      )}

      {/* ---- Controls ---- */}
      <div className="flex flex-wrap items-center gap-3 mb-6">
        <button
          className="btn-mono"
          onClick={startDebate}
          disabled={phase === "running"}
          style={{
            background: phase === "running" ? "transparent" : "rgba(250,204,21,0.12)",
            borderColor: phase === "running" ? "rgba(255,255,255,0.08)" : "rgba(250,204,21,0.35)",
            color: phase === "running" ? "#a1a1aa" : "#facc15",
            cursor: phase === "running" ? "not-allowed" : "pointer",
          }}
        >
          {phase === "running" ? "Debating\u2026" : "Start Debate"}
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
            Round {Math.min(currentRound + 1, totalRounds)}/{totalRounds}
          </span>
        )}
      </div>

      {/* ---- Debate rounds ---- */}
      {roundsData.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          {roundsData.map((rd, rIdx) => (
            <div key={`round-${rIdx}`}>
              {/* Round header */}
              <div style={{ ...monoLabel("#a1a1aa"), marginBottom: "0.65rem" }}>
                Round {rIdx + 1}
              </div>

              {/* Two-column PRO vs CON */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "0.65rem",
                }}
              >
                {/* PRO card */}
                {rd.pro && (
                  <div
                    className="debate-pro animate-slide-in"
                    style={{
                      background: "rgba(74,222,128,0.04)",
                      border: "1px solid rgba(74,222,128,0.12)",
                      borderLeftWidth: 3,
                      borderLeftColor: "#4ade80",
                      borderRadius: 8,
                      padding: "0.75rem 0.85rem",
                    }}
                  >
                    <span
                      style={{
                        fontFamily: MONO,
                        fontSize: "0.65rem",
                        color: "#4ade80",
                        fontWeight: 700,
                        textTransform: "uppercase",
                        letterSpacing: "0.06em",
                      }}
                    >
                      PRO
                    </span>
                    <p
                      style={{
                        color: "#e4e4e7",
                        margin: "0.35rem 0 0",
                        fontSize: "0.84rem",
                        lineHeight: 1.6,
                      }}
                    >
                      {rd.pro}
                    </p>
                  </div>
                )}

                {/* CON card */}
                {rd.con ? (
                  <div
                    className="debate-con animate-slide-in"
                    style={{
                      background: "rgba(244,63,94,0.04)",
                      border: "1px solid rgba(244,63,94,0.12)",
                      borderLeftWidth: 3,
                      borderLeftColor: "#f43f5e",
                      borderRadius: 8,
                      padding: "0.75rem 0.85rem",
                    }}
                  >
                    <span
                      style={{
                        fontFamily: MONO,
                        fontSize: "0.65rem",
                        color: "#f43f5e",
                        fontWeight: 700,
                        textTransform: "uppercase",
                        letterSpacing: "0.06em",
                      }}
                    >
                      CON
                    </span>
                    <p
                      style={{
                        color: "#e4e4e7",
                        margin: "0.35rem 0 0",
                        fontSize: "0.84rem",
                        lineHeight: 1.6,
                      }}
                    >
                      {rd.con}
                    </p>
                  </div>
                ) : (
                  /* Placeholder while CON hasn't appeared yet */
                  <div
                    style={{
                      border: "1px dashed rgba(255,255,255,0.08)",
                      borderRadius: 8,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      color: "#a1a1aa",
                      fontFamily: MONO,
                      fontSize: "0.72rem",
                    }}
                  >
                    Waiting for CON...
                  </div>
                )}
              </div>

              {/* Judge card + score bars */}
              {rd.judged && (
                <div className="animate-fade-in" style={{ marginTop: "0.65rem" }}>
                  {/* Judge card */}
                  <div
                    style={{
                      background: "rgba(250,204,21,0.05)",
                      border: "1px solid rgba(250,204,21,0.2)",
                      borderLeftWidth: 3,
                      borderLeftColor: "#facc15",
                      borderRadius: 8,
                      padding: "0.65rem 0.85rem",
                      maxWidth: 500,
                      margin: "0 auto",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "0.5rem",
                        marginBottom: "0.35rem",
                      }}
                    >
                      {mounted && (
                        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                          <circle cx="7" cy="7" r="6" stroke="#facc15" strokeWidth="1.2" fill="none" />
                          <path d="M4.5 6.5 L6 8.5 L9.5 5" stroke="#facc15" strokeWidth="1.2" fill="none" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                      )}
                      <span
                        style={{
                          fontFamily: MONO,
                          fontSize: "0.65rem",
                          color: "#facc15",
                          fontWeight: 700,
                          textTransform: "uppercase",
                          letterSpacing: "0.06em",
                        }}
                      >
                        Judge
                      </span>
                    </div>
                    <p
                      style={{
                        color: "#b4b4bc",
                        margin: 0,
                        fontSize: "0.8rem",
                        lineHeight: 1.55,
                        fontStyle: "italic",
                      }}
                    >
                      {rd.judge.reasoning}
                    </p>
                  </div>

                  {/* Score bars */}
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "0.75rem",
                      marginTop: "0.55rem",
                      maxWidth: 500,
                      margin: "0.55rem auto 0",
                    }}
                  >
                    {/* PRO score */}
                    <span
                      style={{
                        fontFamily: MONO,
                        fontSize: "0.72rem",
                        color: "#4ade80",
                        fontWeight: 600,
                        minWidth: 28,
                        textAlign: "right",
                      }}
                    >
                      {rd.judge.pro.toFixed(1)}
                    </span>
                    <div
                      style={{
                        flex: 1,
                        display: "flex",
                        gap: 3,
                        height: 8,
                      }}
                    >
                      {/* PRO bar */}
                      <div
                        style={{
                          flex: rd.judge.pro,
                          height: "100%",
                          borderRadius: 4,
                          background:
                            rd.judge.pro >= rd.judge.con
                              ? "linear-gradient(90deg, #4ade80, rgba(74,222,128,0.4))"
                              : "rgba(74,222,128,0.25)",
                          transition: "flex 0.5s ease-out",
                        }}
                      />
                      {/* CON bar */}
                      <div
                        style={{
                          flex: rd.judge.con,
                          height: "100%",
                          borderRadius: 4,
                          background:
                            rd.judge.con >= rd.judge.pro
                              ? "linear-gradient(90deg, rgba(244,63,94,0.4), #f43f5e)"
                              : "rgba(244,63,94,0.25)",
                          transition: "flex 0.5s ease-out",
                        }}
                      />
                    </div>
                    {/* CON score */}
                    <span
                      style={{
                        fontFamily: MONO,
                        fontSize: "0.72rem",
                        color: "#f43f5e",
                        fontWeight: 600,
                        minWidth: 28,
                        textAlign: "left",
                      }}
                    >
                      {rd.judge.con.toFixed(1)}
                    </span>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* ---- Placeholder when idle ---- */}
      {phase === "idle" && visibleArgs.length === 0 && (
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
          Press &ldquo;Start Debate&rdquo; to begin
        </div>
      )}

      {/* ---- Final Verdict ---- */}
      {showVerdict && (
        <div
          className="animate-fade-in"
          style={{
            marginTop: "1.5rem",
            background: "rgba(250,204,21,0.06)",
            border: "1px solid rgba(250,204,21,0.25)",
            borderRadius: 10,
            padding: "1rem 1.15rem",
            boxShadow: "0 0 24px rgba(250,204,21,0.08)",
          }}
        >
          {/* Verdict header */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.6rem",
              marginBottom: "0.55rem",
            }}
          >
            {mounted && (
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                <path
                  d="M9 1 L11 6.5 L17 7 L12.5 11 L14 17 L9 13.5 L4 17 L5.5 11 L1 7 L7 6.5 Z"
                  stroke="#facc15"
                  strokeWidth="1.2"
                  fill="rgba(250,204,21,0.15)"
                  strokeLinejoin="round"
                />
              </svg>
            )}
            <span
              style={{
                fontFamily: MONO,
                fontSize: "0.72rem",
                color: "#facc15",
                fontWeight: 700,
                textTransform: "uppercase",
                letterSpacing: "0.08em",
              }}
            >
              Final Verdict
            </span>
          </div>

          {/* Winner line */}
          <p
            style={{
              fontFamily: MONO,
              fontSize: "0.95rem",
              fontWeight: 700,
              color: "#e4e4e7",
              margin: "0 0 0.55rem",
              lineHeight: 1.5,
            }}
          >
            {topic.verdict}
          </p>

          {/* Final score comparison */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.75rem",
              marginBottom: "0.75rem",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
              <span
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  background: "#4ade80",
                  flexShrink: 0,
                }}
              />
              <span style={{ fontFamily: MONO, fontSize: "0.72rem", color: "#4ade80", fontWeight: 600 }}>
                PRO {runningPro.toFixed(1)}
              </span>
            </div>
            <div
              style={{
                flex: 1,
                height: 8,
                borderRadius: 4,
                background: "rgba(255,255,255,0.06)",
                overflow: "hidden",
                display: "flex",
              }}
            >
              {(runningPro + runningCon) > 0 && (
                <>
                  <div
                    style={{
                      width: `${(runningPro / (runningPro + runningCon)) * 100}%`,
                      height: "100%",
                      background: "linear-gradient(90deg, #4ade80, rgba(74,222,128,0.3))",
                      transition: "width 0.5s ease-out",
                    }}
                  />
                  <div
                    style={{
                      width: `${(runningCon / (runningPro + runningCon)) * 100}%`,
                      height: "100%",
                      background: "linear-gradient(90deg, rgba(244,63,94,0.3), #f43f5e)",
                      transition: "width 0.5s ease-out",
                    }}
                  />
                </>
              )}
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
              <span style={{ fontFamily: MONO, fontSize: "0.72rem", color: "#f43f5e", fontWeight: 600 }}>
                CON {runningCon.toFixed(1)}
              </span>
              <span
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  background: "#f43f5e",
                  flexShrink: 0,
                }}
              />
            </div>
          </div>

          {/* Synthesis */}
          <p
            style={{
              color: "#b4b4bc",
              margin: 0,
              fontSize: "0.82rem",
              lineHeight: 1.7,
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
          {judgedRounds}/{totalRounds} rounds
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
              width: `${(judgedRounds / totalRounds) * 100}%`,
              height: "100%",
              borderRadius: 2,
              background:
                judgedRounds === totalRounds
                  ? "#facc15"
                  : "rgba(250,204,21,0.5)",
              transition: "width 0.35s ease-out",
            }}
          />
        </div>
      </div>
    </div>
  );
}
