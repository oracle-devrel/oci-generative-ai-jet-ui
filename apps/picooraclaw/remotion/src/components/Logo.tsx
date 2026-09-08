import React from "react";
import {
  useCurrentFrame,
  useVideoConfig,
  spring,
  interpolate,
  Img,
  staticFile,
} from "remotion";
import { COLORS } from "../theme";

export const Logo: React.FC<{
  size?: number;
  delay?: number;
}> = ({ size = 200, delay = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const entrance = spring({
    frame: frame - delay,
    fps,
    config: { damping: 8 },
  });

  const scale = interpolate(entrance, [0, 1], [0, 1]);
  const rotation = interpolate(entrance, [0, 1], [-180, 0]);

  // Subtle pulse after entrance
  const pulse =
    entrance > 0.95
      ? interpolate(
          frame % (2 * fps),
          [0, fps, 2 * fps],
          [1, 1.05, 1],
        )
      : 1;

  // Glow intensity
  const glowSize = interpolate(
    frame % (3 * fps),
    [0, 1.5 * fps, 3 * fps],
    [20, 50, 20],
  );

  return (
    <div
      style={{
        width: size,
        height: size,
        transform: `scale(${scale * pulse}) rotate(${rotation}deg)`,
        filter: `drop-shadow(0 0 ${glowSize}px ${COLORS.pine70})`,
      }}
    >
      <Img
        src={staticFile("logo.png")}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "contain",
        }}
      />
    </div>
  );
};
