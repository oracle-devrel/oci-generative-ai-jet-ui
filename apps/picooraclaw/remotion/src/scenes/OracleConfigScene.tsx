import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";
import { Background } from "../components/Background";
import { SectionHeader } from "../components/SectionHeader";
import { COLORS, FONTS } from "../theme";


const CONFIG_ROWS = [
  { field: "enabled", env: "PICO_ORACLE_ENABLED", default: "false", note: "Enable backend" },
  { field: "mode", env: "PICO_ORACLE_MODE", default: "freepdb", note: "freepdb or adb" },
  { field: "host", env: "PICO_ORACLE_HOST", default: "localhost", note: "DB host" },
  { field: "port", env: "PICO_ORACLE_PORT", default: "1521", note: "Listener port" },
  { field: "service", env: "PICO_ORACLE_SERVICE", default: "FREEPDB1", note: "Service name" },
  { field: "user", env: "PICO_ORACLE_USER", default: "picooraclaw", note: "DB user" },
  { field: "password", env: "PICO_ORACLE_PASSWORD", default: "-", note: "DB password" },
  { field: "onnxModel", env: "PICO_ORACLE_ONNX_MODEL", default: "ALL_MINILM_L12_V2", note: "Embedding model" },
  { field: "agentId", env: "PICO_ORACLE_AGENT_ID", default: "default", note: "Multi-agent key" },
];

export const OracleConfigScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <AbsoluteFill>
      <Background variant="oracle" />
      <AbsoluteFill
        style={{
          padding: "60px 80px",
          flexDirection: "column",
        }}
      >
        <SectionHeader
          title="Oracle Configuration"
          subtitle="All fields support PICO_ env var overrides"
          accent={COLORS.oracleRed}
        />

        {/* Table header */}
        {(() => {
          const he = spring({ frame: frame - 8, fps, config: { damping: 200 } });
          return (
            <div
              style={{
                opacity: interpolate(he, [0, 1], [0, 1]),
                display: "grid",
                gridTemplateColumns: "140px 280px 180px 1fr",
                gap: 16,
                padding: "12px 20px",
                borderBottom: `2px solid ${COLORS.oracleRed}40`,
                marginBottom: 8,
              }}
            >
              {["Field", "Env Var", "Default", "Notes"].map((h) => (
                <span
                  key={h}
                  style={{
                    fontSize: 28,
                    fontWeight: 700,
                    color: COLORS.oracleRed,
                    fontFamily: FONTS.mono,
                    textTransform: "uppercase",
                    letterSpacing: "0.06em",
                  }}
                >
                  {h}
                </span>
              ))}
            </div>
          );
        })()}

        {/* Table rows */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center" }}>
          {CONFIG_ROWS.map((row, i) => {
            const entrance = spring({
              frame: frame - (15 + i * 3),
              fps,
              config: { damping: 200 },
            });
            return (
              <div
                key={i}
                style={{
                  opacity: interpolate(entrance, [0, 1], [0, 1]),
                  transform: `translateX(${interpolate(entrance, [0, 1], [-20, 0])}px)`,
                  display: "grid",
                  gridTemplateColumns: "140px 280px 180px 1fr",
                  gap: 16,
                  padding: "10px 20px",
                  borderBottom: `1px solid ${COLORS.oracleRed}10`,
                  background: i % 2 === 0 ? `${COLORS.oracleRed}05` : "transparent",
                  borderRadius: 4,
                }}
              >
                <span style={{ fontSize: 30, color: COLORS.white, fontFamily: FONTS.mono, fontWeight: 700 }}>
                  {row.field}
                </span>
                <span style={{ fontSize: 26, color: COLORS.oracleRed, fontFamily: FONTS.mono }}>
                  {row.env}
                </span>
                <span style={{ fontSize: 28, color: COLORS.brand170, fontFamily: FONTS.mono }}>
                  {row.default}
                </span>
                <span style={{ fontSize: 28, color: COLORS.whiteAlpha, fontFamily: FONTS.mono }}>
                  {row.note}
                </span>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
