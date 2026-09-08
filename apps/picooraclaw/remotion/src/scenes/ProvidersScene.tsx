import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";
import { Background } from "../components/Background";
import { SectionHeader } from "../components/SectionHeader";
import { COLORS, FONTS } from "../theme";

const PROVIDERS = [
  { name: "Ollama", desc: "Local-first, default", icon: "🦙", color: COLORS.brand170 },
  { name: "OpenAI", desc: "GPT-4o compatible", icon: "🤖", color: COLORS.pine70 },
  { name: "Anthropic", desc: "Claude models", icon: "🧠", color: COLORS.pine70 },
  { name: "Groq", desc: "Ultra-fast inference", icon: "⚡", color: COLORS.brand170 },
  { name: "OCI GenAI", desc: "Oracle Cloud", icon: "☁️", color: COLORS.pine70 },
  { name: "Codex CLI", desc: "Code generation", icon: "💻", color: COLORS.whiteAlpha },
];

export const ProvidersScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <AbsoluteFill>
      <Background />
      <AbsoluteFill
        style={{
          padding: "60px 100px",
          flexDirection: "column",
        }}
      >
        <SectionHeader
          title="6 LLM Backends"
          subtitle="One interface, any model"
          accent={COLORS.pine70}
        />
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, 1fr)",
            gap: 24,
            flex: 1,
            alignContent: "center",
            maxWidth: 1200,
            margin: "0 auto",
            width: "100%",
          }}
        >
          {PROVIDERS.map((p, i) => {
            const entrance = spring({
              frame: frame - (15 + i * 6),
              fps,
              config: { damping: 20, stiffness: 200 },
            });
            const opacity = interpolate(entrance, [0, 1], [0, 1]);
            const scale = interpolate(entrance, [0, 1], [0.8, 1]);
            const translateY = interpolate(entrance, [0, 1], [30, 0]);

            return (
              <div
                key={i}
                style={{
                  opacity,
                  transform: `scale(${scale}) translateY(${translateY}px)`,
                  background: `linear-gradient(135deg, ${COLORS.navyLight}, ${p.color}08)`,
                  border: `1px solid ${p.color}40`,
                  borderRadius: 16,
                  padding: "28px 32px",
                  display: "flex",
                  alignItems: "center",
                  gap: 20,
                }}
              >
                <span style={{ fontSize: 88 }}>{p.icon}</span>
                <div>
                  <div
                    style={{
                      fontSize: 48,
                      fontWeight: 700,
                      color: p.color,
                      fontFamily: FONTS.heading,
                    }}
                  >
                    {p.name}
                  </div>
                  <div
                    style={{
                      fontSize: 28,
                      color: COLORS.whiteAlpha,
                      fontFamily: FONTS.mono,
                      marginTop: 4,
                    }}
                  >
                    {p.desc}
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
