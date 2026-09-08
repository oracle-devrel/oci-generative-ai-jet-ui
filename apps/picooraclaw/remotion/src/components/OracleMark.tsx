import React from "react";
import {
  useCurrentFrame,
  useVideoConfig,
  spring,
  interpolate,
} from "remotion";
import { COLORS, FONTS } from "../theme";

// Oracle brand mark: red pill shape + ORACLE wordmark
// Inspired by the official Oracle logo (red arc + wordmark)
export const OracleMark: React.FC<{
  size?: number;
  delay?: number;
  showWordmark?: boolean;
}> = ({ size = 40, delay = 0, showWordmark = false }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const entrance = spring({
    frame: frame - delay,
    fps,
    config: { damping: 200 },
  });

  const opacity = interpolate(entrance, [0, 1], [0, 1]);

  // Subtle red glow pulse
  const glowPulse = interpolate(
    frame % (3 * fps),
    [0, 1.5 * fps, 3 * fps],
    [0, 8, 0],
  );

  return (
    <div
      style={{
        opacity,
        display: "flex",
        alignItems: "center",
        gap: size * 0.35,
        filter: `drop-shadow(0 0 ${glowPulse}px ${COLORS.oracleRed})`,
      }}
    >
      {/* Oracle red mark with arc motif */}
      <svg width={size} height={size} viewBox="0 0 48 48">
        {/* Red circle base */}
        <circle cx="24" cy="24" r="22" fill={COLORS.oracleRed} />
        {/* White arc accent (top) — echoes Oracle's arc logo */}
        <path
          d="M12 20 Q24 6, 36 20"
          fill="none"
          stroke="#FBF9F8"
          strokeWidth="2.5"
          strokeLinecap="round"
        />
        {/* White "O" letterform */}
        <ellipse
          cx="24"
          cy="27"
          rx="9"
          ry="9"
          fill="none"
          stroke="#FBF9F8"
          strokeWidth="3"
        />
      </svg>
      {showWordmark && (
        <span
          style={{
            fontSize: size * 0.55,
            fontFamily: FONTS.heading,
            fontWeight: 700,
            color: COLORS.oracleRed,
            letterSpacing: "0.12em",
            textTransform: "uppercase",
          }}
        >
          Oracle
        </span>
      )}
    </div>
  );
};

// Subtle corner watermark for non-Oracle scenes
export const OracleWatermark: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const entrance = spring({
    frame: frame - 10,
    fps,
    config: { damping: 200 },
  });

  return (
    <div
      style={{
        position: "absolute",
        bottom: 30,
        right: 40,
        opacity: interpolate(entrance, [0, 1], [0, 0.45]),
        display: "flex",
        alignItems: "center",
        gap: 10,
      }}
    >
      <svg width={20} height={20} viewBox="0 0 48 48">
        <circle cx="24" cy="24" r="22" fill={COLORS.oracleRed} />
        <path d="M12 20 Q24 6, 36 20" fill="none" stroke="#FBF9F8" strokeWidth="2.5" strokeLinecap="round" />
        <ellipse cx="24" cy="27" rx="9" ry="9" fill="none" stroke="#FBF9F8" strokeWidth="3" />
      </svg>
      <span
        style={{
          fontSize: 13,
          fontFamily: FONTS.heading,
          fontWeight: 600,
          color: COLORS.whiteAlpha,
          letterSpacing: "0.06em",
          textTransform: "uppercase",
        }}
      >
        Powered by Oracle AI
      </span>
    </div>
  );
};
