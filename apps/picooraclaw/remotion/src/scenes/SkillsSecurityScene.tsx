import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";
import { Background } from "../components/Background";
import { SectionHeader } from "../components/SectionHeader";
import { COLORS, FONTS } from "../theme";

const TRUSTED = [
  { label: "Full tool access", icon: "🔧" },
  { label: "Workspace skills/", icon: "📁" },
  { label: "Prompt injection", icon: "💉" },
  { label: "Keyword matching", icon: "🔤" },
];

const SANDBOXED = [
  { label: "Read-only access", icon: "👁️" },
  { label: "Trust attenuation", icon: "🔐" },
  { label: "Budget-aware", icon: "💰" },
  { label: "Isolated execution", icon: "📦" },
];

const SKILL_OPS = ["skill_list", "skill_search", "skill_install", "skill_remove"];

export const SkillsSecurityScene: React.FC = () => {
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
          title="Skills & Security"
          subtitle="SKILL.md extensions with trust boundaries"
          accent={COLORS.teal70}
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
          {/* Trusted Skills */}
          <div
            style={{
              flex: 1,
              maxWidth: 450,
            }}
          >
            {(() => {
              const e = spring({ frame: frame - 10, fps, config: { damping: 200 } });
              return (
                <div
                  style={{
                    opacity: interpolate(e, [0, 1], [0, 1]),
                    background: `${COLORS.teal70}08`,
                    border: `1px solid ${COLORS.teal70}30`,
                    borderRadius: 16,
                    padding: "28px 32px",
                  }}
                >
                  <div
                    style={{
                      fontSize: 48,
                      fontWeight: 800,
                      color: COLORS.teal70,
                      fontFamily: FONTS.heading,
                      marginBottom: 20,
                    }}
                  >
                    Trusted Skills
                  </div>
                  {TRUSTED.map((t, i) => {
                    const te = spring({ frame: frame - (20 + i * 5), fps, config: { damping: 200 } });
                    return (
                      <div
                        key={i}
                        style={{
                          opacity: interpolate(te, [0, 1], [0, 1]),
                          display: "flex",
                          alignItems: "center",
                          gap: 14,
                          padding: "10px 0",
                          fontSize: 34,
                          color: COLORS.white,
                          fontFamily: FONTS.mono,
                        }}
                      >
                        <span style={{ fontSize: 44 }}>{t.icon}</span>
                        {t.label}
                      </div>
                    );
                  })}
                </div>
              );
            })()}
          </div>

          {/* VS divider */}
          {(() => {
            const e = spring({ frame: frame - 25, fps, config: { damping: 15, stiffness: 200 } });
            return (
              <div
                style={{
                  opacity: interpolate(e, [0, 1], [0, 1]),
                  transform: `scale(${interpolate(e, [0, 1], [0.5, 1])})`,
                  fontSize: 56,
                  fontWeight: 800,
                  color: COLORS.whiteAlpha,
                  fontFamily: FONTS.heading,
                }}
              >
                VS
              </div>
            );
          })()}

          {/* Sandboxed Skills */}
          <div style={{ flex: 1, maxWidth: 450 }}>
            {(() => {
              const e = spring({ frame: frame - 15, fps, config: { damping: 200 } });
              return (
                <div
                  style={{
                    opacity: interpolate(e, [0, 1], [0, 1]),
                    background: `${COLORS.pine70}08`,
                    border: `1px solid ${COLORS.pine70}30`,
                    borderRadius: 16,
                    padding: "28px 32px",
                  }}
                >
                  <div
                    style={{
                      fontSize: 48,
                      fontWeight: 800,
                      color: COLORS.pine70,
                      fontFamily: FONTS.heading,
                      marginBottom: 20,
                    }}
                  >
                    Installed Skills
                  </div>
                  {SANDBOXED.map((s, i) => {
                    const se = spring({ frame: frame - (25 + i * 5), fps, config: { damping: 200 } });
                    return (
                      <div
                        key={i}
                        style={{
                          opacity: interpolate(se, [0, 1], [0, 1]),
                          display: "flex",
                          alignItems: "center",
                          gap: 14,
                          padding: "10px 0",
                          fontSize: 34,
                          color: COLORS.white,
                          fontFamily: FONTS.mono,
                        }}
                      >
                        <span style={{ fontSize: 44 }}>{s.icon}</span>
                        {s.label}
                      </div>
                    );
                  })}
                </div>
              );
            })()}
          </div>
        </div>

        {/* Skill operation badges */}
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            gap: 16,
            marginTop: 10,
            marginBottom: 20,
          }}
        >
          {SKILL_OPS.map((op, i) => {
            const e = spring({ frame: frame - (50 + i * 4), fps, config: { damping: 200 } });
            return (
              <div
                key={i}
                style={{
                  opacity: interpolate(e, [0, 1], [0, 1]),
                  transform: `translateY(${interpolate(e, [0, 1], [15, 0])}px)`,
                  background: `${COLORS.navyLight}`,
                  border: `1px solid ${COLORS.whiteAlpha}`,
                  borderRadius: 20,
                  padding: "8px 18px",
                  fontSize: 28,
                  color: COLORS.whiteAlpha,
                  fontFamily: FONTS.mono,
                }}
              >
                {op}
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
