import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";
import { Background } from "../components/Background";
import { GlowText } from "../components/AnimatedText";
import { COLORS, FONTS } from "../theme";

const TABLES = [
  "PICO_SESSIONS",
  "PICO_TRANSCRIPTS",
  "PICO_STATE",
  "PICO_MEMORIES",
  "PICO_PROMPTS",
  "PICO_SKILLS",
  "PICO_EMBEDDINGS",
  "PICO_CRON_JOBS",
];

export const OracleScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <AbsoluteFill>
      <Background variant="oracle" />
      <AbsoluteFill
        style={{
          padding: "60px 100px",
          flexDirection: "column",
          alignItems: "center",
        }}
      >
        {/* Oracle branding */}
        <div style={{ textAlign: "center", marginBottom: 20 }}>
          <GlowText
            text="Oracle AI Database"
            delay={5}
            fontSize={128}
            color={COLORS.oracleRed}
            glowColor={COLORS.oracleRedGlow}
          />
          <div
            style={{
              fontSize: 44,
              color: COLORS.whiteAlpha,
              fontFamily: FONTS.mono,
              marginTop: 12,
            }}
          >
            <GlowText
              text="The storage layer that makes it shine"
              delay={20}
              fontSize={44}
              color={COLORS.whiteAlpha}
              glowColor="transparent"
            />
          </div>
        </div>

        {/* 8 Oracle Tables grid */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(4, 1fr)",
            gap: 16,
            marginTop: 30,
            maxWidth: 1200,
          }}
        >
          {TABLES.map((table, i) => {
            const entrance = spring({
              frame: frame - (30 + i * 5),
              fps,
              config: { damping: 15, stiffness: 200 },
            });
            const opacity = interpolate(entrance, [0, 1], [0, 1]);
            const scale = interpolate(entrance, [0, 1], [0.6, 1]);

            return (
              <div
                key={i}
                style={{
                  opacity,
                  transform: `scale(${scale})`,
                  background: `linear-gradient(135deg, ${COLORS.oracleRed}15, ${COLORS.navyLight})`,
                  border: `1px solid ${COLORS.oracleRed}40`,
                  borderRadius: 12,
                  padding: "20px 24px",
                  textAlign: "center",
                }}
              >
                <div
                  style={{
                    fontSize: 28,
                    fontFamily: FONTS.mono,
                    color: COLORS.oracleRed,
                    fontWeight: 700,
                    letterSpacing: "0.03em",
                  }}
                >
                  {table}
                </div>
              </div>
            );
          })}
        </div>

        {/* Features row */}
        <div
          style={{
            display: "flex",
            gap: 40,
            marginTop: 40,
            justifyContent: "center",
          }}
        >
          {[
            { icon: "🔄", text: "ACID Transactions" },
            { icon: "🧠", text: "ONNX Embeddings" },
            { icon: "🔌", text: "Pure Go Driver" },
            { icon: "🔙", text: "Graceful Fallback" },
          ].map((feat, i) => {
            const entrance = spring({
              frame: frame - (60 + i * 8),
              fps,
              config: { damping: 200 },
            });
            return (
              <div
                key={i}
                style={{
                  opacity: interpolate(entrance, [0, 1], [0, 1]),
                  transform: `translateY(${interpolate(entrance, [0, 1], [20, 0])}px)`,
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  fontSize: 36,
                  color: COLORS.white,
                  fontFamily: FONTS.mono,
                }}
              >
                <span style={{ fontSize: 56 }}>{feat.icon}</span>
                {feat.text}
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
