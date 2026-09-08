import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";
import { Background } from "../components/Background";
import { SectionHeader } from "../components/SectionHeader";
import { COLORS, FONTS } from "../theme";

const INSPECT_CMDS = [
  { sub: "oracle-inspect", desc: "Overview dashboard", icon: "📊" },
  { sub: "oracle-inspect memories", desc: "List all memories", icon: "🧠" },
  { sub: "oracle-inspect memories -s \"...\"", desc: "Semantic search", icon: "🔍" },
  { sub: "oracle-inspect sessions", desc: "Chat history", icon: "💬" },
  { sub: "oracle-inspect transcripts", desc: "Full audit log", icon: "📝" },
  { sub: "oracle-inspect state", desc: "Agent key-value state", icon: "💾" },
  { sub: "oracle-inspect daily-notes", desc: "Journal entries + vectors", icon: "📓" },
  { sub: "oracle-inspect prompts", desc: "System prompts", icon: "📋" },
  { sub: "oracle-inspect config", desc: "Runtime configuration", icon: "⚙️" },
  { sub: "oracle-inspect schema", desc: "ONNX models + indexes", icon: "🏗️" },
];

export const InspectScene: React.FC = () => {
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
          title="Oracle Inspect"
          subtitle="Full visibility into your agent's stored data"
          accent={COLORS.oracleRed}
        />
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(2, 1fr)",
            gap: 12,
            flex: 1,
            alignContent: "center",
            maxWidth: 1300,
            margin: "0 auto",
            width: "100%",
          }}
        >
          {INSPECT_CMDS.map((c, i) => {
            const entrance = spring({
              frame: frame - (12 + i * 4),
              fps,
              config: { damping: 200 },
            });
            return (
              <div
                key={i}
                style={{
                  opacity: interpolate(entrance, [0, 1], [0, 1]),
                  transform: `translateX(${interpolate(entrance, [0, 1], [i % 2 === 0 ? -30 : 30, 0])}px)`,
                  background: `${COLORS.oracleRed}08`,
                  border: `1px solid ${COLORS.oracleRed}20`,
                  borderRadius: 10,
                  padding: "14px 20px",
                  display: "flex",
                  alignItems: "center",
                  gap: 14,
                }}
              >
                <span style={{ fontSize: 48, flexShrink: 0 }}>{c.icon}</span>
                <div>
                  <div
                    style={{
                      fontFamily: FONTS.mono,
                      fontSize: 28,
                      color: COLORS.oracleRed,
                      fontWeight: 700,
                    }}
                  >
                    $ {c.sub}
                  </div>
                  <div
                    style={{
                      fontFamily: FONTS.mono,
                      fontSize: 26,
                      color: COLORS.whiteAlpha,
                      marginTop: 2,
                    }}
                  >
                    {c.desc}
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
