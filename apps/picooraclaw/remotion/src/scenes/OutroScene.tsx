import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";
import { Background } from "../components/Background";
import { Logo } from "../components/Logo";
import { GlowText, FadeInText } from "../components/AnimatedText";
import { COLORS, FONTS } from "../theme";

export const OutroScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // GitHub link entrance
  const linkEntrance = spring({
    frame: frame - 2 * fps,
    fps,
    config: { damping: 200 },
  });

  const taglineEntrance = spring({
    frame: frame - 2.5 * fps,
    fps,
    config: { damping: 200 },
  });

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
        <Logo size={140} delay={5} />

        <GlowText
          text="Get Started"
          delay={15}
          fontSize={144}
          color={COLORS.white}
          glowColor={COLORS.blueGlow}
        />

        {/* Install command */}
        <div
          style={{
            opacity: interpolate(linkEntrance, [0, 1], [0, 1]),
            transform: `translateY(${interpolate(linkEntrance, [0, 1], [30, 0])}px)`,
            background: `${COLORS.navyLight}`,
            border: `1px solid ${COLORS.pine70}40`,
            borderRadius: 12,
            padding: "18px 40px",
            display: "flex",
            alignItems: "center",
            gap: 12,
          }}
        >
          <span style={{ color: COLORS.brand170, fontSize: 40, fontFamily: FONTS.mono }}>$</span>
          <span style={{ color: COLORS.white, fontSize: 40, fontFamily: FONTS.mono }}>
            go install github.com/jasperan/picooraclaw@latest
          </span>
        </div>

        {/* GitHub URL */}
        <FadeInText
          text="github.com/jasperan/picooraclaw"
          delay={Math.round(2.2 * fps)}
          fontSize={48}
          color={COLORS.pine70}
          fontFamily={FONTS.mono}
        />

        {/* Tagline */}
        <div
          style={{
            opacity: interpolate(taglineEntrance, [0, 1], [0, 1]),
            fontSize: 40,
            color: COLORS.whiteAlpha,
            fontFamily: FONTS.mono,
            fontStyle: "italic",
            marginTop: 10,
          }}
        >
          Every bit helps, every bit matters.
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
