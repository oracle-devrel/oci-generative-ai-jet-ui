import React from "react";
import {
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from "remotion";
import { COLORS, FONTS } from "../theme";

export const FadeInText: React.FC<{
  text: string;
  delay?: number;
  fontSize?: number;
  color?: string;
  fontFamily?: string;
  fontWeight?: string | number;
  style?: React.CSSProperties;
}> = ({
  text,
  delay = 0,
  fontSize = 96,
  color = COLORS.white,
  fontFamily = FONTS.heading,
  fontWeight = "bold",
  style = {},
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const entrance = spring({
    frame: frame - delay,
    fps,
    config: { damping: 200 },
  });

  const opacity = interpolate(entrance, [0, 1], [0, 1]);
  const translateY = interpolate(entrance, [0, 1], [40, 0]);

  return (
    <div
      style={{
        fontSize,
        color,
        fontFamily,
        fontWeight,
        opacity,
        transform: `translateY(${translateY}px)`,
        ...style,
      }}
    >
      {text}
    </div>
  );
};

export const TypewriterText: React.FC<{
  text: string;
  delay?: number;
  speed?: number;
  fontSize?: number;
  color?: string;
  style?: React.CSSProperties;
}> = ({
  text,
  delay = 0,
  speed = 2,
  fontSize = 64,
  color = COLORS.whiteAlpha,
  style = {},
}) => {
  const frame = useCurrentFrame();

  const charsToShow = Math.min(
    Math.floor(Math.max(0, frame - delay) / speed),
    text.length,
  );

  const showCursor = Math.floor(frame / 15) % 2 === 0;

  return (
    <div
      style={{
        fontSize,
        color,
        fontFamily: FONTS.mono,
        letterSpacing: "0.02em",
        ...style,
      }}
    >
      {text.slice(0, charsToShow)}
      {charsToShow < text.length && (
        <span style={{ opacity: showCursor ? 1 : 0 }}>|</span>
      )}
    </div>
  );
};

export const GlowText: React.FC<{
  text: string;
  delay?: number;
  fontSize?: number;
  color?: string;
  glowColor?: string;
  style?: React.CSSProperties;
}> = ({
  text,
  delay = 0,
  fontSize = 144,
  color = COLORS.brand170,
  glowColor = COLORS.limeGlow,
  style = {},
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const entrance = spring({
    frame: frame - delay,
    fps,
    config: { damping: 15, stiffness: 200 },
  });

  const scale = interpolate(entrance, [0, 1], [0.8, 1]);
  const opacity = interpolate(entrance, [0, 1], [0, 1]);

  // Pulse glow
  const glowIntensity = interpolate(
    frame % (2 * fps),
    [0, fps, 2 * fps],
    [20, 40, 20],
  );

  return (
    <div
      style={{
        fontSize,
        color,
        fontFamily: FONTS.heading,
        fontWeight: 800,
        opacity,
        transform: `scale(${scale})`,
        textShadow: `0 0 ${glowIntensity}px ${glowColor}`,
        ...style,
      }}
    >
      {text}
    </div>
  );
};
