import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";
import { Background } from "../components/Background";
import { SectionHeader } from "../components/SectionHeader";
import { COLORS, FONTS } from "../theme";

const FEATURES = [
  {
    title: "Voice Input",
    subtitle: "Groq Whisper Transcription",
    icon: "🎙️",
    color: COLORS.pine70,
    details: [
      "Real-time speech-to-text",
      "Multi-language support",
      "Low-latency Groq inference",
    ],
  },
  {
    title: "Cron Scheduler",
    subtitle: "Background Task Automation",
    icon: "⏰",
    color: COLORS.brand170,
    details: [
      "Standard cron expressions",
      "Interval-based scheduling",
      "Persistent across restarts",
    ],
  },
  {
    title: "Heartbeat",
    subtitle: "Periodic Agent Actions",
    icon: "💓",
    color: COLORS.pine70,
    details: [
      "Reads HEARTBEAT.md config",
      "Autonomous periodic tasks",
      "Health monitoring built-in",
    ],
  },
];

export const VoiceCronScene: React.FC = () => {
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
          title="Voice, Cron & Heartbeat"
          subtitle="Beyond chat: autonomous capabilities"
          accent={COLORS.brand170}
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
          {FEATURES.map((f, fi) => {
            const entrance = spring({
              frame: frame - (12 + fi * 10),
              fps,
              config: { damping: 15, stiffness: 200 },
            });
            const opacity = interpolate(entrance, [0, 1], [0, 1]);
            const scale = interpolate(entrance, [0, 1], [0.8, 1]);

            return (
              <div
                key={fi}
                style={{
                  opacity,
                  transform: `scale(${scale})`,
                  background: `${f.color}08`,
                  border: `1px solid ${f.color}30`,
                  borderRadius: 18,
                  padding: "32px 28px",
                  flex: 1,
                  maxWidth: 380,
                }}
              >
                <span style={{ fontSize: 96 }}>{f.icon}</span>
                <div
                  style={{
                    fontSize: 52,
                    fontWeight: 800,
                    color: f.color,
                    fontFamily: FONTS.heading,
                    marginTop: 16,
                  }}
                >
                  {f.title}
                </div>
                <div
                  style={{
                    fontSize: 28,
                    color: COLORS.whiteAlpha,
                    fontFamily: FONTS.mono,
                    marginTop: 4,
                    marginBottom: 20,
                  }}
                >
                  {f.subtitle}
                </div>
                {f.details.map((d, di) => {
                  const detailEntrance = spring({
                    frame: frame - (25 + fi * 10 + di * 5),
                    fps,
                    config: { damping: 200 },
                  });
                  return (
                    <div
                      key={di}
                      style={{
                        opacity: interpolate(detailEntrance, [0, 1], [0, 1]),
                        display: "flex",
                        alignItems: "center",
                        gap: 10,
                        padding: "6px 0",
                        fontSize: 30,
                        color: COLORS.white,
                        fontFamily: FONTS.mono,
                      }}
                    >
                      <div
                        style={{
                          width: 6,
                          height: 6,
                          borderRadius: "50%",
                          backgroundColor: f.color,
                          flexShrink: 0,
                        }}
                      />
                      {d}
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
