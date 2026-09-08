import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";
import { Background } from "../components/Background";
import { Logo } from "../components/Logo";
import { GlowText, TypewriterText } from "../components/AnimatedText";
import { COLORS, FONTS } from "../theme";

export const TitleScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Version badge entrance
  const badgeEntrance = spring({
    frame: frame - 2.5 * fps,
    fps,
    config: { damping: 200 },
  });

  const badgeOpacity = interpolate(badgeEntrance, [0, 1], [0, 1]);
  const badgeY = interpolate(badgeEntrance, [0, 1], [20, 0]);

  return (
    <AbsoluteFill>
      <Background />
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          flexDirection: "column",
          gap: 30,
        }}
      >
        <Logo size={180} delay={5} />

        <GlowText
          text="PicoOraClaw"
          delay={Math.round(0.8 * fps)}
          fontSize={192}
          color={COLORS.white}
          glowColor={COLORS.blueGlow}
          style={{ letterSpacing: "-0.02em" }}
        />

        <TypewriterText
          text="Ultra-lightweight AI assistant powered by Oracle AI Database"
          delay={Math.round(1.5 * fps)}
          speed={1.5}
          fontSize={56}
          color={COLORS.whiteAlpha}
          style={{ maxWidth: 800, textAlign: "center" }}
        />

        {/* Version badge */}
        <div
          style={{
            opacity: badgeOpacity,
            transform: `translateY(${badgeY}px)`,
            display: "flex",
            gap: 16,
            marginTop: 10,
          }}
        >
          <span
            style={{
              background: `${COLORS.pine70}20`,
              border: `1px solid ${COLORS.pine70}50`,
              borderRadius: 20,
              padding: "8px 20px",
              fontSize: 32,
              color: COLORS.pine70,
              fontFamily: FONTS.mono,
            }}
          >
            Go 1.24
          </span>
          <span
            style={{
              background: `${COLORS.brand170}15`,
              border: `1px solid ${COLORS.brand170}40`,
              borderRadius: 20,
              padding: "8px 20px",
              fontSize: 32,
              color: COLORS.brand170,
              fontFamily: FONTS.mono,
            }}
          >
            ~10MB RAM
          </span>
          <span
            style={{
              background: `${COLORS.pine70}20`,
              border: `1px solid ${COLORS.pine70}50`,
              borderRadius: 20,
              padding: "8px 20px",
              fontSize: 32,
              color: COLORS.pine70,
              fontFamily: FONTS.mono,
            }}
          >
            Oracle AI DB
          </span>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
