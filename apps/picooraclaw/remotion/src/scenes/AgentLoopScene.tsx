import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";
import { Background } from "../components/Background";
import { SectionHeader } from "../components/SectionHeader";
import { COLORS, FONTS } from "../theme";

const STEPS = [
  { icon: "💬", label: "User Message", desc: "CLI, channel, or heartbeat" },
  { icon: "🧠", label: "Context Builder", desc: "IDENTITY + SOUL + TOOLS" },
  { icon: "📜", label: "Session History", desc: "Load conversation state" },
  { icon: "🤖", label: "LLM Provider", desc: "Call via provider interface" },
  { icon: "🔧", label: "Tool Execution", desc: "ToolRegistry dispatch" },
  { icon: "✅", label: "Response", desc: "Return to originating channel" },
];

export const AgentLoopScene: React.FC = () => {
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
          title="Agent Loop"
          subtitle="From message to response in milliseconds"
          accent={COLORS.brand170}
        />
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flex: 1,
            gap: 0,
          }}
        >
          {STEPS.map((step, i) => {
            const entrance = spring({
              frame: frame - (20 + i * 10),
              fps,
              config: { damping: 200 },
            });

            const opacity = interpolate(entrance, [0, 1], [0, 1]);
            const translateY = interpolate(entrance, [0, 1], [50, 0]);

            // Arrow animation
            const arrowEntrance = spring({
              frame: frame - (25 + i * 10),
              fps,
              config: { damping: 200 },
            });
            const arrowWidth = interpolate(arrowEntrance, [0, 1], [0, 40]);

            return (
              <React.Fragment key={i}>
                <div
                  style={{
                    opacity,
                    transform: `translateY(${translateY}px)`,
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    gap: 12,
                    minWidth: 150,
                  }}
                >
                  <div
                    style={{
                      width: 70,
                      height: 70,
                      borderRadius: "50%",
                      background: `${COLORS.pine70}20`,
                      border: `2px solid ${COLORS.pine70}60`,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 64,
                    }}
                  >
                    {step.icon}
                  </div>
                  <span
                    style={{
                      fontSize: 32,
                      fontWeight: 700,
                      color: COLORS.white,
                      fontFamily: FONTS.heading,
                      textAlign: "center",
                    }}
                  >
                    {step.label}
                  </span>
                  <span
                    style={{
                      fontSize: 24,
                      color: COLORS.whiteAlpha,
                      fontFamily: FONTS.mono,
                      textAlign: "center",
                    }}
                  >
                    {step.desc}
                  </span>
                </div>
                {i < STEPS.length - 1 && (
                  <div
                    style={{
                      width: arrowWidth,
                      height: 2,
                      background: `linear-gradient(90deg, ${COLORS.pine70}, ${COLORS.brand170})`,
                      marginBottom: 40,
                      opacity: arrowEntrance,
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
