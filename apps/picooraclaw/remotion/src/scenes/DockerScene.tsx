import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";
import { Background } from "../components/Background";
import { SectionHeader } from "../components/SectionHeader";
import { COLORS, FONTS } from "../theme";

const DOCKER_COMMANDS = [
  {
    label: "Full Stack (Oracle + Gateway)",
    cmd: "docker compose --profile oracle --profile gateway up -d",
    color: COLORS.oracleRed,
  },
  {
    label: "Gateway Only (no Oracle)",
    cmd: "docker compose --profile gateway up -d",
    color: COLORS.pine70,
  },
  {
    label: "One-Shot Chat",
    cmd: "docker compose run --rm picoclaw-agent -m \"2+2?\"",
    color: COLORS.teal70,
  },
];

const DOCKER_FEATURES = [
  { icon: "📦", text: "Multi-stage Alpine image" },
  { icon: "🔄", text: "Auto-restart on failure" },
  { icon: "🗂️", text: "Volume-mapped config" },
  { icon: "🌐", text: "Network-isolated services" },
  { icon: "🔒", text: "Env var secrets" },
  { icon: "📊", text: "Health check endpoints" },
];

export const DockerScene: React.FC = () => {
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
          title="Docker & Compose"
          subtitle="Container-ready with profile-based service selection"
          accent={COLORS.pine70}
        />
        <div
          style={{
            display: "flex",
            gap: 40,
            flex: 1,
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {/* Commands */}
          <div style={{ flex: 1.2, display: "flex", flexDirection: "column", gap: 16 }}>
            {DOCKER_COMMANDS.map((dc, i) => {
              const entrance = spring({
                frame: frame - (15 + i * 10),
                fps,
                config: { damping: 200 },
              });
              return (
                <div
                  key={i}
                  style={{
                    opacity: interpolate(entrance, [0, 1], [0, 1]),
                    transform: `translateX(${interpolate(entrance, [0, 1], [-50, 0])}px)`,
                  }}
                >
                  <div
                    style={{
                      fontSize: 28,
                      color: dc.color,
                      fontFamily: FONTS.mono,
                      marginBottom: 6,
                      fontWeight: 700,
                    }}
                  >
                    {dc.label}
                  </div>
                  <div
                    style={{
                      background: COLORS.navyLight,
                      border: `1px solid ${dc.color}25`,
                      borderRadius: 10,
                      padding: "14px 20px",
                      fontFamily: FONTS.mono,
                      fontSize: 28,
                      color: COLORS.white,
                    }}
                  >
                    <span style={{ color: COLORS.teal70 }}>$ </span>
                    {dc.cmd}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Features */}
          <div
            style={{
              flex: 0.8,
              display: "grid",
              gridTemplateColumns: "repeat(2, 1fr)",
              gap: 14,
            }}
          >
            {DOCKER_FEATURES.map((f, i) => {
              const entrance = spring({
                frame: frame - (25 + i * 4),
                fps,
                config: { damping: 20, stiffness: 200 },
              });
              return (
                <div
                  key={i}
                  style={{
                    opacity: interpolate(entrance, [0, 1], [0, 1]),
                    transform: `scale(${interpolate(entrance, [0, 1], [0.7, 1])})`,
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                    fontSize: 30,
                    color: COLORS.white,
                    fontFamily: FONTS.mono,
                  }}
                >
                  <span style={{ fontSize: 44 }}>{f.icon}</span>
                  {f.text}
                </div>
              );
            })}
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
