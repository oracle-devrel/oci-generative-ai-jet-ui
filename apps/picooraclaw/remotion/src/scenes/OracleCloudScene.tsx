import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";
import { Background } from "../components/Background";
import { GlowText } from "../components/AnimatedText";
import { COLORS, FONTS } from "../theme";


const STACK_ITEMS = [
  { layer: "OCI Compute", desc: "ARM A1.Flex (Always Free eligible)", icon: "🖥️" },
  { layer: "Ollama", desc: "gemma3:270m auto-loaded for CPU inference", icon: "🦙" },
  { layer: "Oracle AI DB", desc: "Free container with ONNX embeddings", icon: "🗄️" },
  { layer: "PicoOraClaw Gateway", desc: "systemd service on port 18790", icon: "🚀" },
];

const TIMELINE = [
  { time: "0:00", event: "Click Deploy button" },
  { time: "2:00", event: "Compute instance provisioned" },
  { time: "4:00", event: "Docker pulls complete" },
  { time: "6:00", event: "Oracle DB ready, schema initialized" },
  { time: "8:00", event: "Gateway live, ready to chat" },
];

export const OracleCloudScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <AbsoluteFill>
      <Background variant="oracle" />
      <AbsoluteFill
        style={{
          padding: "60px 100px",
          flexDirection: "column",
          alignItems: "center",
        }}
      >
        <GlowText
          text="One-Click Cloud Deploy"
          delay={5}
          fontSize={104}
          color={COLORS.oracleRed}
          glowColor={COLORS.oracleRedGlow}
        />
        <div
          style={{
            fontSize: 40,
            color: COLORS.whiteAlpha,
            fontFamily: FONTS.mono,
            marginTop: 8,
            marginBottom: 30,
          }}
        >
          <GlowText
            text="OCI Resource Manager does the heavy lifting"
            delay={15}
            fontSize={40}
            color={COLORS.whiteAlpha}
            glowColor="transparent"
          />
        </div>

        <div
          style={{
            display: "flex",
            gap: 50,
            flex: 1,
            alignItems: "center",
            width: "100%",
            maxWidth: 1400,
          }}
        >
          {/* Stack layers */}
          <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 14 }}>
            {STACK_ITEMS.map((s, i) => {
              const entrance = spring({
                frame: frame - (20 + i * 8),
                fps,
                config: { damping: 200 },
              });
              return (
                <div
                  key={i}
                  style={{
                    opacity: interpolate(entrance, [0, 1], [0, 1]),
                    transform: `translateX(${interpolate(entrance, [0, 1], [-50, 0])}px)`,
                    background: `${COLORS.oracleRed}10`,
                    border: `1px solid ${COLORS.oracleRed}30`,
                    borderRadius: 14,
                    padding: "20px 24px",
                    display: "flex",
                    alignItems: "center",
                    gap: 18,
                  }}
                >
                  <span style={{ fontSize: 64 }}>{s.icon}</span>
                  <div>
                    <div
                      style={{
                        fontSize: 40,
                        fontWeight: 700,
                        color: COLORS.oracleRed,
                        fontFamily: FONTS.heading,
                      }}
                    >
                      {s.layer}
                    </div>
                    <div
                      style={{
                        fontSize: 28,
                        color: COLORS.whiteAlpha,
                        fontFamily: FONTS.mono,
                        marginTop: 2,
                      }}
                    >
                      {s.desc}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Timeline */}
          <div style={{ flex: 0.8 }}>
            {(() => {
              const headerE = spring({ frame: frame - 25, fps, config: { damping: 200 } });
              return (
                <div
                  style={{
                    opacity: interpolate(headerE, [0, 1], [0, 1]),
                    fontSize: 44,
                    fontWeight: 800,
                    color: COLORS.white,
                    fontFamily: FONTS.heading,
                    marginBottom: 20,
                  }}
                >
                  Deploy Timeline
                </div>
              );
            })()}
            {TIMELINE.map((t, i) => {
              const entrance = spring({
                frame: frame - (35 + i * 6),
                fps,
                config: { damping: 200 },
              });
              return (
                <div
                  key={i}
                  style={{
                    opacity: interpolate(entrance, [0, 1], [0, 1]),
                    display: "flex",
                    alignItems: "center",
                    gap: 16,
                    padding: "10px 0",
                    borderLeft: `2px solid ${COLORS.oracleRed}40`,
                    paddingLeft: 20,
                    marginLeft: 10,
                  }}
                >
                  <span
                    style={{
                      fontFamily: FONTS.mono,
                      fontSize: 32,
                      color: COLORS.oracleRed,
                      fontWeight: 700,
                      minWidth: 50,
                    }}
                  >
                    {t.time}
                  </span>
                  <span
                    style={{
                      fontFamily: FONTS.mono,
                      fontSize: 30,
                      color: COLORS.white,
                    }}
                  >
                    {t.event}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
