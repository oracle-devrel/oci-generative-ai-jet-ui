import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";
import { Background } from "../components/Background";
import { SectionHeader } from "../components/SectionHeader";
import { COLORS, FONTS } from "../theme";

const COMMANDS = [
  { cmd: "onboard", desc: "Init config + workspace", cat: "setup" },
  { cmd: "agent -m '...'", desc: "One-shot chat", cat: "chat" },
  { cmd: "agent", desc: "Interactive REPL", cat: "chat" },
  { cmd: "gateway", desc: "Long-running service", cat: "service" },
  { cmd: "setup-oracle", desc: "Init Oracle schema + ONNX", cat: "oracle" },
  { cmd: "oracle-inspect", desc: "Inspect stored data", cat: "oracle" },
  { cmd: "status", desc: "Show system status", cat: "info" },
  { cmd: "cron list", desc: "Scheduled jobs", cat: "service" },
  { cmd: "skills list", desc: "Installed skills", cat: "info" },
  { cmd: "seed-demo", desc: "Load demo data", cat: "setup" },
];

const CAT_COLORS: Record<string, string> = {
  setup: COLORS.brand170,
  chat: COLORS.pine70,
  service: COLORS.pine70,
  oracle: COLORS.oracleRed,
  info: COLORS.whiteAlpha,
};

export const CLICommandsScene: React.FC = () => {
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
        <SectionHeader title="CLI Commands" subtitle="Every action from the terminal" />
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(2, 1fr)",
            gap: 12,
            flex: 1,
            alignContent: "center",
            maxWidth: 1300,
            margin: "0 auto",
            width: "100%",
          }}
        >
          {COMMANDS.map((c, i) => {
            const entrance = spring({
              frame: frame - (12 + i * 3),
              fps,
              config: { damping: 200 },
            });
            const catColor = CAT_COLORS[c.cat] || COLORS.whiteAlpha;
            return (
              <div
                key={i}
                style={{
                  opacity: interpolate(entrance, [0, 1], [0, 1]),
                  transform: `translateY(${interpolate(entrance, [0, 1], [20, 0])}px)`,
                  background: COLORS.navyLight,
                  border: `1px solid ${catColor}20`,
                  borderRadius: 10,
                  padding: "14px 20px",
                  display: "flex",
                  alignItems: "center",
                  gap: 14,
                }}
              >
                <span
                  style={{
                    color: COLORS.brand170,
                    fontFamily: FONTS.mono,
                    fontSize: 28,
                    flexShrink: 0,
                  }}
                >
                  $
                </span>
                <span
                  style={{
                    color: catColor,
                    fontFamily: FONTS.mono,
                    fontSize: 32,
                    fontWeight: 700,
                    minWidth: 200,
                  }}
                >
                  picooraclaw {c.cmd}
                </span>
                <span
                  style={{
                    color: COLORS.whiteAlpha,
                    fontFamily: FONTS.mono,
                    fontSize: 28,
                  }}
                >
                  {c.desc}
                </span>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
