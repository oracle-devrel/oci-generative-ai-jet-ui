import React from "react";
import {
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  Easing,
} from "remotion";
import { COLORS, FONTS } from "../theme";

export const MetricCounter: React.FC<{
  value: string;
  label: string;
  delay?: number;
  color?: string;
  numericValue?: number;
  prefix?: string;
  suffix?: string;
}> = ({
  value,
  label,
  delay = 0,
  color = COLORS.brand170,
  numericValue,
  prefix = "",
  suffix = "",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const entrance = spring({
    frame: frame - delay,
    fps,
    config: { damping: 200 },
  });

  const opacity = interpolate(entrance, [0, 1], [0, 1]);
  const translateY = interpolate(entrance, [0, 1], [60, 0]);
  const scale = interpolate(entrance, [0, 1], [0.5, 1]);

  // Animated counter
  let displayValue = value;
  if (numericValue !== undefined) {
    const countProgress = interpolate(
      frame - delay,
      [0, 1.5 * fps],
      [0, numericValue],
      {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
        easing: Easing.out(Easing.quad),
      },
    );
    displayValue = `${prefix}${Math.round(countProgress)}${suffix}`;
  }

  return (
    <div
      style={{
        opacity,
        transform: `translateY(${translateY}px) scale(${scale})`,
        textAlign: "center",
        padding: "20px 30px",
      }}
    >
      <div
        style={{
          fontSize: 144,
          fontWeight: 800,
          color,
          fontFamily: FONTS.heading,
          textShadow: `0 0 30px ${color}40`,
          lineHeight: 1,
        }}
      >
        {displayValue}
      </div>
      <div
        style={{
          fontSize: 40,
          color: COLORS.whiteAlpha,
          fontFamily: FONTS.mono,
          marginTop: 12,
          letterSpacing: "0.05em",
          textTransform: "uppercase",
        }}
      >
        {label}
      </div>
    </div>
  );
};
