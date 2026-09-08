import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";
import { Background } from "../components/Background";
import { SectionHeader } from "../components/SectionHeader";
import { COLORS, FONTS } from "../theme";

const PACKAGES = [
  { name: "agent", desc: "Core loop", color: COLORS.pine70 },
  { name: "providers", desc: "LLM backends", color: COLORS.pine70 },
  { name: "tools", desc: "15 built-in", color: COLORS.teal70 },
  { name: "channels", desc: "10 platforms", color: COLORS.teal70 },
  { name: "oracle", desc: "AI Database", color: COLORS.pine70 },
  { name: "config", desc: "Settings", color: COLORS.whiteAlpha },
  { name: "bus", desc: "Message bus", color: COLORS.whiteAlpha },
  { name: "session", desc: "History", color: COLORS.pine70 },
  { name: "state", desc: "Key-value", color: COLORS.pine70 },
  { name: "cron", desc: "Scheduled", color: COLORS.teal70 },
  { name: "heartbeat", desc: "Periodic", color: COLORS.brand170 },
  { name: "skills", desc: "Extensions", color: COLORS.brand170 },
  { name: "voice", desc: "Whisper", color: COLORS.pine70 },
  { name: "health", desc: "HTTP", color: COLORS.whiteAlpha },
  { name: "auth", desc: "OAuth", color: COLORS.whiteAlpha },
  { name: "migrate", desc: "Migration", color: COLORS.whiteAlpha },
  { name: "devices", desc: "USB/HW", color: COLORS.brand170 },
  { name: "logger", desc: "Structured", color: COLORS.whiteAlpha },
];

export const ArchitectureScene: React.FC = () => {
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
          title="23 Packages"
          subtitle="Clean, modular Go architecture"
        />
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 12,
            justifyContent: "center",
            alignContent: "center",
            flex: 1,
            maxWidth: 1500,
            margin: "0 auto",
          }}
        >
          {PACKAGES.map((pkg, i) => {
            const entrance = spring({
              frame: frame - (15 + i * 2),
              fps,
              config: { damping: 20, stiffness: 200 },
            });

            const opacity = interpolate(entrance, [0, 1], [0, 1]);
            const scale = interpolate(entrance, [0, 1], [0.5, 1]);

            return (
              <div
                key={i}
                style={{
                  opacity,
                  transform: `scale(${scale})`,
                  background: `${pkg.color}10`,
                  border: `1px solid ${pkg.color}40`,
                  borderRadius: 12,
                  padding: "14px 22px",
                  display: "flex",
                  flexDirection: "column",
                  gap: 4,
                  minWidth: 140,
                }}
              >
                <span
                  style={{
                    fontSize: 36,
                    fontFamily: FONTS.mono,
                    color: pkg.color,
                    fontWeight: 700,
                  }}
                >
                  {pkg.name}
                </span>
                <span
                  style={{
                    fontSize: 26,
                    fontFamily: FONTS.mono,
                    color: COLORS.whiteAlpha,
                  }}
                >
                  {pkg.desc}
                </span>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
