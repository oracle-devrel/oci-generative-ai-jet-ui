import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";
import { Background } from "../components/Background";
import { SectionHeader } from "../components/SectionHeader";
import { COLORS, FONTS } from "../theme";

const DEVICES = [
  { name: "Raspberry Pi", arch: "ARM64", ram: "1-8GB", icon: "🍓", color: COLORS.teal70 },
  { name: "RISC-V SBCs", arch: "rv64gc", ram: "512MB+", icon: "🔬", color: COLORS.pine70 },
  { name: "MaixCAM", arch: "RISC-V", ram: "Vision AI", icon: "📷", color: COLORS.teal70 },
  { name: "BeagleBone", arch: "ARM", ram: "512MB", icon: "🦴", color: COLORS.pine70 },
  { name: "Jetson Nano", arch: "ARM64", ram: "2-4GB", icon: "🟢", color: COLORS.teal70 },
  { name: "ESP32-S3", arch: "Xtensa", ram: "8MB PSRAM", icon: "📡", color: COLORS.pine70 },
];

export const EmbeddedTargetsScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Central badge animation
  const badgeEntrance = spring({
    frame: frame - 5,
    fps,
    config: { damping: 15, stiffness: 200 },
  });

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
          title="Embedded Targets"
          subtitle="Runs on hardware you can hold in your hand"
        />

        {/* Center: binary size badge */}
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            marginBottom: 30,
          }}
        >
          <div
            style={{
              opacity: interpolate(badgeEntrance, [0, 1], [0, 1]),
              transform: `scale(${interpolate(badgeEntrance, [0, 1], [0.5, 1])})`,
              background: `${COLORS.teal70}15`,
              border: `2px solid ${COLORS.teal70}50`,
              borderRadius: 30,
              padding: "12px 40px",
              fontSize: 40,
              fontWeight: 800,
              color: COLORS.teal70,
              fontFamily: FONTS.heading,
              textAlign: "center",
            }}
          >
            Single static binary, ~10MB RAM, zero dependencies
          </div>
        </div>

        {/* Device grid */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, 1fr)",
            gap: 20,
            flex: 1,
            alignContent: "center",
            maxWidth: 1200,
            margin: "0 auto",
            width: "100%",
          }}
        >
          {DEVICES.map((d, i) => {
            const entrance = spring({
              frame: frame - (20 + i * 5),
              fps,
              config: { damping: 20, stiffness: 200 },
            });
            return (
              <div
                key={i}
                style={{
                  opacity: interpolate(entrance, [0, 1], [0, 1]),
                  transform: `scale(${interpolate(entrance, [0, 1], [0.7, 1])})`,
                  background: `${d.color}08`,
                  border: `1px solid ${d.color}25`,
                  borderRadius: 14,
                  padding: "22px 24px",
                  display: "flex",
                  alignItems: "center",
                  gap: 16,
                }}
              >
                <span style={{ fontSize: 72 }}>{d.icon}</span>
                <div>
                  <div style={{ fontSize: 40, fontWeight: 700, color: d.color, fontFamily: FONTS.heading }}>
                    {d.name}
                  </div>
                  <div style={{ fontSize: 26, color: COLORS.whiteAlpha, fontFamily: FONTS.mono, marginTop: 2 }}>
                    {d.arch} / {d.ram}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
