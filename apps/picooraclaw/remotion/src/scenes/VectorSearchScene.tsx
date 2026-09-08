import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";
import { Background } from "../components/Background";
import { SectionHeader } from "../components/SectionHeader";
import { COLORS, FONTS } from "../theme";

export const VectorSearchScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Animated dots representing vector space
  const dots = Array.from({ length: 30 }, (_, i) => ({
    x: 150 + (i % 6) * 140 + Math.sin(i * 2.1) * 40,
    y: 100 + Math.floor(i / 6) * 120 + Math.cos(i * 1.7) * 30,
    size: 8 + (i % 3) * 4,
    isQuery: i === 14,
    isMatch: [13, 15, 8, 20].includes(i),
  }));

  return (
    <AbsoluteFill>
      <Background variant="oracle" />
      <AbsoluteFill
        style={{
          padding: "60px 100px",
          flexDirection: "row",
        }}
      >
        {/* Left side: text */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center" }}>
          <SectionHeader
            title="AI Vector Search"
            subtitle="Semantic memory with VECTOR_EMBEDDING()"
            accent={COLORS.oracleRed}
          />

          {/* SQL snippet */}
          {(() => {
            const codeEntrance = spring({
              frame: frame - 30,
              fps,
              config: { damping: 200 },
            });
            return (
              <div
                style={{
                  opacity: interpolate(codeEntrance, [0, 1], [0, 1]),
                  transform: `translateY(${interpolate(codeEntrance, [0, 1], [30, 0])}px)`,
                  background: `${COLORS.navyLight}`,
                  border: `1px solid ${COLORS.oracleRed}30`,
                  borderRadius: 12,
                  padding: "24px 28px",
                  fontFamily: FONTS.mono,
                  fontSize: 30,
                  color: COLORS.whiteAlpha,
                  lineHeight: 1.8,
                  maxWidth: 600,
                }}
              >
                <span style={{ color: COLORS.pine70 }}>SELECT</span> content,{"\n"}
                {"  "}<span style={{ color: COLORS.oracleRed }}>VECTOR_DISTANCE</span>(embedding,{"\n"}
                {"    "}<span style={{ color: COLORS.oracleRed }}>VECTOR_EMBEDDING</span>(
                <span style={{ color: COLORS.teal70 }}>onnx_model</span>{"\n"}
                {"      "}USING <span style={{ color: COLORS.teal70 }}>'query text'</span>)){"\n"}
                <span style={{ color: COLORS.pine70 }}>FROM</span> PICO_MEMORIES{"\n"}
                <span style={{ color: COLORS.pine70 }}>ORDER BY</span> distance <span style={{ color: COLORS.pine70 }}>ASC</span>
              </div>
            );
          })()}
        </div>

        {/* Right side: vector visualization */}
        <div
          style={{
            flex: 1,
            position: "relative",
          }}
        >
          {dots.map((dot, i) => {
            const entrance = spring({
              frame: frame - (15 + i * 1.5),
              fps,
              config: { damping: 20, stiffness: 200 },
            });
            const opacity = interpolate(entrance, [0, 1], [0, 1]);
            const scale = interpolate(entrance, [0, 1], [0, 1]);

            // Pulse for query dot
            const pulse = dot.isQuery
              ? interpolate(frame % (fps), [0, fps / 2, fps], [1, 1.5, 1])
              : 1;

            // Connection lines to matches
            const lineOpacity = dot.isMatch
              ? interpolate(
                  spring({ frame: frame - 60, fps, config: { damping: 200 } }),
                  [0, 1],
                  [0, 0.4],
                )
              : 0;

            const color = dot.isQuery
              ? COLORS.oracleRed
              : dot.isMatch
                ? COLORS.teal70
                : `${COLORS.pine70}60`;

            return (
              <React.Fragment key={i}>
                {dot.isMatch && (
                  <svg
                    style={{
                      position: "absolute",
                      top: 0,
                      left: 0,
                      width: "100%",
                      height: "100%",
                      opacity: lineOpacity,
                    }}
                  >
                    <line
                      x1={dots[14].x}
                      y1={dots[14].y}
                      x2={dot.x}
                      y2={dot.y}
                      stroke={COLORS.teal70}
                      strokeWidth={2}
                      strokeDasharray="6,4"
                    />
                  </svg>
                )}
                <div
                  style={{
                    position: "absolute",
                    left: dot.x,
                    top: dot.y,
                    width: dot.size,
                    height: dot.size,
                    borderRadius: "50%",
                    backgroundColor: color,
                    opacity,
                    transform: `scale(${scale * pulse})`,
                    boxShadow: dot.isQuery
                      ? `0 0 20px ${COLORS.oracleRed}`
                      : dot.isMatch
                        ? `0 0 12px ${COLORS.teal70}`
                        : "none",
                  }}
                />
              </React.Fragment>
            );
          })}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
