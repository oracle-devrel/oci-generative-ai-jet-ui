import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";
import { Background } from "../components/Background";
import { SectionHeader } from "../components/SectionHeader";
import { COLORS, FONTS } from "../theme";

const STEPS = [
  { step: "1", cmd: "make build", desc: "Build single binary (Go 1.24+)", icon: "🔨" },
  { step: "2", cmd: "picooraclaw onboard", desc: "Initialize config + workspace", icon: "📋" },
  { step: "3", cmd: "ollama pull qwen3:latest", desc: "Download your LLM", icon: "🦙" },
  { step: "4", cmd: "edit config.json", desc: "Point to Ollama endpoint", icon: "⚙️" },
  { step: "5", cmd: "picooraclaw agent", desc: "Start chatting", icon: "💬" },
];

export const QuickstartScene: React.FC = () => {
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
          title="5-Minute Quickstart"
          subtitle="From zero to chatting in five steps"
          accent={COLORS.teal70}
        />
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 16,
            flex: 1,
            justifyContent: "center",
            maxWidth: 900,
            margin: "0 auto",
            width: "100%",
          }}
        >
          {STEPS.map((s, i) => {
            const entrance = spring({
              frame: frame - (15 + i * 10),
              fps,
              config: { damping: 200 },
            });
            const opacity = interpolate(entrance, [0, 1], [0, 1]);
            const translateX = interpolate(entrance, [0, 1], [-60, 0]);

            // Connector line
            const lineEntrance = spring({
              frame: frame - (20 + i * 10),
              fps,
              config: { damping: 200 },
            });

            return (
              <React.Fragment key={i}>
                <div
                  style={{
                    opacity,
                    transform: `translateX(${translateX}px)`,
                    display: "flex",
                    alignItems: "center",
                    gap: 20,
                  }}
                >
                  {/* Step number */}
                  <div
                    style={{
                      width: 48,
                      height: 48,
                      borderRadius: "50%",
                      background: `${COLORS.teal70}20`,
                      border: `2px solid ${COLORS.teal70}60`,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 40,
                      fontWeight: 800,
                      color: COLORS.teal70,
                      fontFamily: FONTS.heading,
                      flexShrink: 0,
                    }}
                  >
                    {s.step}
                  </div>
                  {/* Command */}
                  <div
                    style={{
                      background: COLORS.navyLight,
                      border: `1px solid ${COLORS.pine70}20`,
                      borderRadius: 10,
                      padding: "14px 24px",
                      flex: 1,
                      display: "flex",
                      alignItems: "center",
                      gap: 16,
                    }}
                  >
                    <span style={{ fontSize: 48 }}>{s.icon}</span>
                    <div>
                      <div
                        style={{
                          fontSize: 36,
                          fontFamily: FONTS.mono,
                          color: COLORS.teal70,
                          fontWeight: 700,
                        }}
                      >
                        $ {s.cmd}
                      </div>
                      <div
                        style={{
                          fontSize: 28,
                          fontFamily: FONTS.mono,
                          color: COLORS.whiteAlpha,
                          marginTop: 4,
                        }}
                      >
                        {s.desc}
                      </div>
                    </div>
                  </div>
                </div>
                {i < STEPS.length - 1 && (
                  <div
                    style={{
                      width: 2,
                      height: interpolate(lineEntrance, [0, 1], [0, 12]),
                      backgroundColor: `${COLORS.teal70}30`,
                      marginLeft: 23,
                    }}
                  />
                )}
              </React.Fragment>
            );
          })}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
