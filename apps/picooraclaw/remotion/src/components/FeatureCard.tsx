import React from "react";
import { useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";
import { COLORS, FONTS } from "../theme";

export const FeatureCard: React.FC<{
  icon: string;
  title: string;
  delay?: number;
  accentColor?: string;
  small?: boolean;
}> = ({
  icon,
  title,
  delay = 0,
  accentColor = COLORS.pine70,
  small = false,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const entrance = spring({
    frame: frame - delay,
    fps,
    config: { damping: 20, stiffness: 200 },
  });

  const opacity = interpolate(entrance, [0, 1], [0, 1]);
  const scale = interpolate(entrance, [0, 1], [0.7, 1]);

  return (
    <div
      style={{
        opacity,
        transform: `scale(${scale})`,
        background: `linear-gradient(135deg, ${COLORS.navyLight}, ${COLORS.navy})`,
        border: `1px solid ${accentColor}30`,
        borderRadius: 16,
        padding: small ? "16px 20px" : "24px 32px",
        display: "flex",
        alignItems: "center",
        gap: small ? 12 : 16,
        minWidth: small ? 160 : 220,
      }}
    >
      <span style={{ fontSize: small ? 56 : 72 }}>{icon}</span>
      <span
        style={{
          fontSize: small ? 32 : 40,
          color: COLORS.white,
          fontFamily: FONTS.mono,
          fontWeight: 500,
        }}
      >
        {title}
      </span>
    </div>
  );
};

export const FeatureGrid: React.FC<{
  items: Array<{ icon: string; title: string }>;
  columns?: number;
  staggerDelay?: number;
  baseDelay?: number;
  accentColor?: string;
  small?: boolean;
}> = ({
  items,
  columns = 4,
  staggerDelay = 3,
  baseDelay = 15,
  accentColor,
  small = false,
}) => {
  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        gap: small ? 12 : 20,
        justifyContent: "center",
        maxWidth: 1400,
      }}
    >
      {items.map((item, i) => (
        <FeatureCard
          key={i}
          icon={item.icon}
          title={item.title}
          delay={baseDelay + i * staggerDelay}
          accentColor={accentColor}
          small={small}
        />
      ))}
    </div>
  );
};
