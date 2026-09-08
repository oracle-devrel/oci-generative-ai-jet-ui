import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";
import { Background } from "../components/Background";
import { SectionHeader } from "../components/SectionHeader";
import { COLORS, FONTS } from "../theme";

const PROJECTS = [
  {
    name: "PicoOraClaw",
    lang: "Go",
    upstream: "PicoClaw",
    status: "This project",
    icon: "🦞",
    color: COLORS.brand170,
    active: true,
  },
  {
    name: "OraClaw",
    lang: "TypeScript / Node.js",
    upstream: "OpenClaw",
    status: "Production-ready",
    icon: "🦀",
    color: COLORS.pine70,
    active: false,
  },
  {
    name: "ZeroOraClaw",
    lang: "Python",
    upstream: "ZeroClaw",
    status: "In development",
    icon: "🐍",
    color: COLORS.brand170,
    active: false,
  },
];

export const SisterProjectsScene: React.FC = () => {
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
          title="The Oracle Agent Family"
          subtitle="Oracle AI Database as the storage layer across languages"
        />
        <div
          style={{
            display: "flex",
            gap: 30,
            flex: 1,
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {PROJECTS.map((p, i) => {
            const entrance = spring({
              frame: frame - (12 + i * 10),
              fps,
              config: { damping: 15, stiffness: 200 },
            });
            const opacity = interpolate(entrance, [0, 1], [0, 1]);
            const scale = interpolate(entrance, [0, 1], [0.7, 1]);

            return (
              <div
                key={i}
                style={{
                  opacity,
                  transform: `scale(${scale})`,
                  background: p.active
                    ? `linear-gradient(135deg, ${p.color}15, ${COLORS.navyLight})`
                    : `${COLORS.navyLight}`,
                  border: `${p.active ? 2 : 1}px solid ${p.color}${p.active ? "60" : "25"}`,
                  borderRadius: 18,
                  padding: "36px 32px",
                  flex: 1,
                  maxWidth: 380,
                  textAlign: "center",
                }}
              >
                <span style={{ fontSize: 112 }}>{p.icon}</span>
                <div
                  style={{
                    fontSize: 56,
                    fontWeight: 800,
                    color: p.color,
                    fontFamily: FONTS.heading,
                    marginTop: 16,
                  }}
                >
                  {p.name}
                </div>
                <div
                  style={{
                    fontSize: 32,
                    color: COLORS.white,
                    fontFamily: FONTS.mono,
                    marginTop: 8,
                  }}
                >
                  {p.lang}
                </div>
                <div
                  style={{
                    fontSize: 26,
                    color: COLORS.whiteAlpha,
                    fontFamily: FONTS.mono,
                    marginTop: 4,
                  }}
                >
                  Fork of {p.upstream}
                </div>
                <div
                  style={{
                    marginTop: 16,
                    display: "inline-block",
                    background: `${p.color}15`,
                    border: `1px solid ${p.color}30`,
                    borderRadius: 16,
                    padding: "6px 16px",
                    fontSize: 26,
                    color: p.color,
                    fontFamily: FONTS.mono,
                  }}
                >
                  {p.status}
                </div>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
