import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate } from "remotion";
import { COLORS } from "../theme";

export const Background: React.FC<{
  variant?: "navy" | "dark" | "oracle";
}> = ({ variant = "navy" }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // All variants use the same Slate 170 base
  const bgColor = COLORS.navy;

  const isOracle = variant === "oracle";
  const glowColor = isOracle ? COLORS.oracleRedGlow : COLORS.blueGlow;
  const secondaryGlow = isOracle ? COLORS.oracleRedGlow : "rgba(137, 178, 128, 0.15)";

  // Slow rotating gradient
  const rotation = interpolate(frame, [0, 10 * fps], [0, 360], {
    extrapolateRight: "extend",
  });

  // Subtle pulsing glow
  const glowOpacity = interpolate(
    frame % (4 * fps),
    [0, 2 * fps, 4 * fps],
    [0.08, 0.18, 0.08],
  );

  return (
    <AbsoluteFill
      style={{
        backgroundColor: bgColor,
        overflow: "hidden",
      }}
    >
      {/* Primary radial glow */}
      <div
        style={{
          position: "absolute",
          width: "120%",
          height: "120%",
          top: "-10%",
          left: "-10%",
          background: `radial-gradient(ellipse at 30% 20%, ${glowColor} 0%, transparent 60%)`,
          opacity: glowOpacity,
          transform: `rotate(${rotation}deg)`,
        }}
      />
      {/* Secondary glow */}
      <div
        style={{
          position: "absolute",
          width: "100%",
          height: "100%",
          background: `radial-gradient(ellipse at 70% 80%, ${secondaryGlow} 0%, transparent 50%)`,
          opacity: glowOpacity * 0.5,
        }}
      />
      {/* Subtle dot grid */}
      <div
        style={{
          position: "absolute",
          width: "100%",
          height: "100%",
          backgroundImage: `radial-gradient(circle, rgba(241,239,237,0.025) 1px, transparent 1px)`,
          backgroundSize: "28px 28px",
        }}
      />
    </AbsoluteFill>
  );
};
