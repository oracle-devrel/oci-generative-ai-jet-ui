import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";
import { Background } from "../components/Background";
import { SectionHeader } from "../components/SectionHeader";
import { COLORS, FONTS } from "../theme";


const REASONS = [
  {
    title: "In-Database ONNX Embeddings",
    desc: "384-dim ALL_MINILM_L12_V2 runs inside the DB. No external API calls.",
    icon: "🧠",
  },
  {
    title: "AI Vector Search",
    desc: "VECTOR_DISTANCE with cosine similarity, indexed for sub-millisecond lookups.",
    icon: "🔍",
  },
  {
    title: "ACID Transactions",
    desc: "Real transaction guarantees. Memory writes are atomic, not eventual.",
    icon: "🔒",
  },
  {
    title: "Multi-Agent Isolation",
    desc: "Each agent gets its own namespace via agent_id. No cross-contamination.",
    icon: "🏗️",
  },
  {
    title: "Graceful Fallback",
    desc: "Oracle down? Automatically switches to file-based storage. Zero downtime.",
    icon: "🛡️",
  },
];

export const WhyOracleScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <AbsoluteFill>
      <Background variant="oracle" />
      <AbsoluteFill
        style={{
          padding: "60px 100px",
          flexDirection: "column",
        }}
      >
        <SectionHeader
          title="Why Oracle AI Database"
          accent={COLORS.oracleRed}
        />
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 18,
            flex: 1,
            justifyContent: "center",
            maxWidth: 1200,
            margin: "0 auto",
            width: "100%",
          }}
        >
          {REASONS.map((r, i) => {
            const entrance = spring({
              frame: frame - (12 + i * 8),
              fps,
              config: { damping: 200 },
            });
            const opacity = interpolate(entrance, [0, 1], [0, 1]);
            const translateX = interpolate(entrance, [0, 1], [-80, 0]);

            return (
              <div
                key={i}
                style={{
                  opacity,
                  transform: `translateX(${translateX}px)`,
                  display: "flex",
                  alignItems: "center",
                  gap: 24,
                  background: `${COLORS.oracleRed}08`,
                  border: `1px solid ${COLORS.oracleRed}25`,
                  borderRadius: 14,
                  padding: "20px 28px",
                }}
              >
                <span style={{ fontSize: 72, flexShrink: 0 }}>{r.icon}</span>
                <div>
                  <div
                    style={{
                      fontSize: 44,
                      fontWeight: 700,
                      color: COLORS.oracleRed,
                      fontFamily: FONTS.heading,
                    }}
                  >
                    {r.title}
                  </div>
                  <div
                    style={{
                      fontSize: 32,
                      color: COLORS.whiteAlpha,
                      fontFamily: FONTS.mono,
                      marginTop: 4,
                    }}
                  >
                    {r.desc}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
