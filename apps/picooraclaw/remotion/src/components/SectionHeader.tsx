import React from "react";
import {
  useCurrentFrame,
  useVideoConfig,
  spring,
  interpolate,
} from "remotion";
import { COLORS, FONTS } from "../theme";

export const SectionHeader: React.FC<{
  title: string;
  subtitle?: string;
  accent?: string;
  delay?: number;
}> = ({ title, subtitle, accent = COLORS.pine70, delay = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const entrance = spring({
    frame: frame - delay,
    fps,
    config: { damping: 200 },
  });

  const opacity = interpolate(entrance, [0, 1], [0, 1]);
  const translateX = interpolate(entrance, [0, 1], [-80, 0]);

  // Accent line width
  const lineWidth = interpolate(entrance, [0, 1], [0, 120]);

  return (
    <div style={{ opacity, marginBottom: 40 }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 20,
          transform: `translateX(${translateX}px)`,
        }}
      >
        <div
          style={{
            width: lineWidth,
            height: 4,
            background: accent,
            borderRadius: 2,
          }}
        />
        <h2
          style={{
            fontSize: 112,
            fontFamily: FONTS.heading,
            fontWeight: 800,
            color: COLORS.white,
            margin: 0,
          }}
        >
          {title}
        </h2>
      </div>
      {subtitle && (
        <p
          style={{
            fontSize: 44,
            color: COLORS.whiteAlpha,
            fontFamily: FONTS.mono,
            marginTop: 12,
            marginLeft: 140,
            transform: `translateX(${translateX}px)`,
          }}
        >
          {subtitle}
        </p>
      )}
    </div>
  );
};
