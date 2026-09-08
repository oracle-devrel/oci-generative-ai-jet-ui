import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";
import { Background } from "../components/Background";
import { SectionHeader } from "../components/SectionHeader";
import { COLORS, FONTS } from "../theme";

const DIFFERENTIATORS = [
  {
    title: "Interface-Driven Architecture",
    desc: "Every component swappable via Go interfaces",
    icon: "🔌",
    color: COLORS.pine70,
  },
  {
    title: "Oracle AI Vector Search",
    desc: "Semantic memory with in-database ONNX embeddings",
    icon: "🧠",
    color: COLORS.pine70,
  },
  {
    title: "Hardware-Native",
    desc: "I2C, SPI, USB device tools built-in",
    icon: "🔬",
    color: COLORS.teal70,
  },
  {
    title: "Zero CGO Dependencies",
    desc: "Pure Go, single static binary, no Instant Client",
    icon: "📦",
    color: COLORS.pine70,
  },
  {
    title: "Graceful Degradation",
    desc: "Oracle fails? Falls back to file-based storage",
    icon: "🛡️",
    color: COLORS.teal70,
  },
  {
    title: "Skill System",
    desc: "SKILL.md extensions from workspace, global, or GitHub",
    icon: "⚡",
    color: COLORS.teal70,
  },
];

export const UniqueScene: React.FC = () => {
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
          title="What Makes It Unique"
          accent={COLORS.teal70}
        />
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, 1fr)",
            gap: 20,
            flex: 1,
            alignContent: "center",
            maxWidth: 1400,
            margin: "0 auto",
            width: "100%",
          }}
        >
          {DIFFERENTIATORS.map((d, i) => {
            const entrance = spring({
              frame: frame - (10 + i * 6),
              fps,
              config: { damping: 15, stiffness: 200 },
            });
            const opacity = interpolate(entrance, [0, 1], [0, 1]);
            const scale = interpolate(entrance, [0, 1], [0.8, 1]);

            return (
              <div
                key={i}
                style={{
                  opacity,
                  transform: `scale(${scale})`,
                  background: `linear-gradient(135deg, ${d.color}10, ${COLORS.navyLight})`,
                  border: `1px solid ${d.color}30`,
                  borderRadius: 16,
                  padding: "28px 28px",
                }}
              >
                <span style={{ fontSize: 72 }}>{d.icon}</span>
                <div
                  style={{
                    fontSize: 40,
                    fontWeight: 700,
                    color: d.color,
                    fontFamily: FONTS.heading,
                    marginTop: 12,
                  }}
                >
                  {d.title}
                </div>
                <div
                  style={{
                    fontSize: 28,
                    color: COLORS.whiteAlpha,
                    fontFamily: FONTS.mono,
                    marginTop: 8,
                    lineHeight: 1.5,
                  }}
                >
                  {d.desc}
                </div>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
