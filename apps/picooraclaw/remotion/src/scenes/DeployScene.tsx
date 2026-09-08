import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";
import { Background } from "../components/Background";
import { SectionHeader } from "../components/SectionHeader";
import { COLORS, FONTS } from "../theme";

const TARGETS = [
  { arch: "x86_64", icon: "🖥️", desc: "Desktop & Server" },
  { arch: "ARM64", icon: "📱", desc: "Raspberry Pi, phones" },
  { arch: "RISC-V", icon: "🔬", desc: "Embedded Linux" },
  { arch: "macOS", icon: "🍎", desc: "Apple Silicon" },
  { arch: "Windows", icon: "🪟", desc: "x86_64" },
];

const DEPLOY_OPTIONS = [
  { method: "Binary", desc: "Single executable, zero deps", icon: "📦" },
  { method: "Docker", desc: "Multi-stage alpine image", icon: "🐳" },
  { method: "OCI Stack", desc: "One-click Resource Manager", icon: "☁️" },
  { method: "Embed", desc: "Flash to device ROM", icon: "💾" },
];

export const DeployScene: React.FC = () => {
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
          title="Deploy Anywhere"
          subtitle="Cross-compile to 5 targets with make build-all"
        />

        <div
          style={{
            display: "flex",
            gap: 60,
            flex: 1,
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {/* Architectures column */}
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {TARGETS.map((t, i) => {
              const entrance = spring({
                frame: frame - (15 + i * 6),
                fps,
                config: { damping: 200 },
              });
              return (
                <div
                  key={i}
                  style={{
                    opacity: interpolate(entrance, [0, 1], [0, 1]),
                    transform: `translateX(${interpolate(entrance, [0, 1], [-60, 0])}px)`,
                    display: "flex",
                    alignItems: "center",
                    gap: 16,
                    background: `${COLORS.pine70}10`,
                    border: `1px solid ${COLORS.pine70}30`,
                    borderRadius: 12,
                    padding: "14px 24px",
                    minWidth: 280,
                  }}
                >
                  <span style={{ fontSize: 56 }}>{t.icon}</span>
                  <div>
                    <div style={{ fontSize: 40, fontWeight: 700, color: COLORS.pine70, fontFamily: FONTS.heading }}>
                      {t.arch}
                    </div>
                    <div style={{ fontSize: 26, color: COLORS.whiteAlpha, fontFamily: FONTS.mono }}>
                      {t.desc}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Center divider */}
          {(() => {
            const lineEntrance = spring({
              frame: frame - 30,
              fps,
              config: { damping: 200 },
            });
            const lineHeight = interpolate(lineEntrance, [0, 1], [0, 400]);
            return (
              <div
                style={{
                  width: 2,
                  height: lineHeight,
                  background: `linear-gradient(180deg, ${COLORS.pine70}, ${COLORS.brand170})`,
                  opacity: 0.4,
                }}
              />
            );
          })()}

          {/* Deploy methods column */}
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {DEPLOY_OPTIONS.map((d, i) => {
              const entrance = spring({
                frame: frame - (20 + i * 6),
                fps,
                config: { damping: 200 },
              });
              return (
                <div
                  key={i}
                  style={{
                    opacity: interpolate(entrance, [0, 1], [0, 1]),
                    transform: `translateX(${interpolate(entrance, [0, 1], [60, 0])}px)`,
                    display: "flex",
                    alignItems: "center",
                    gap: 16,
                    background: `${COLORS.brand170}08`,
                    border: `1px solid ${COLORS.brand170}30`,
                    borderRadius: 12,
                    padding: "14px 24px",
                    minWidth: 320,
                  }}
                >
                  <span style={{ fontSize: 56 }}>{d.icon}</span>
                  <div>
                    <div style={{ fontSize: 40, fontWeight: 700, color: COLORS.brand170, fontFamily: FONTS.heading }}>
                      {d.method}
                    </div>
                    <div style={{ fontSize: 26, color: COLORS.whiteAlpha, fontFamily: FONTS.mono }}>
                      {d.desc}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
