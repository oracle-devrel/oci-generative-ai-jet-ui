import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";
import { Background } from "../components/Background";
import { SectionHeader } from "../components/SectionHeader";
import { COLORS, FONTS } from "../theme";

const TOOL_INTERFACE = [
  { line: "type Tool interface {", color: COLORS.pine70 },
  { line: "    Name() string", color: COLORS.white },
  { line: "    Description() string", color: COLORS.white },
  { line: "    Parameters() []Param", color: COLORS.white },
  { line: "    Execute(ctx, args) Result", color: COLORS.brand170 },
  { line: "}", color: COLORS.pine70 },
];

const CHANNEL_INTERFACE = [
  { line: "type Channel interface {", color: COLORS.pine70 },
  { line: "    Name() string", color: COLORS.white },
  { line: "    Listen(ctx) <-chan Message", color: COLORS.white },
  { line: "    Send(ctx, msg) error", color: COLORS.brand170 },
  { line: "}", color: COLORS.pine70 },
];

const PROVIDER_INTERFACE = [
  { line: "type LLMProvider interface {", color: COLORS.pine70 },
  { line: "    Chat(msgs, tools) Response", color: COLORS.white },
  { line: "    GetDefaultModel() string", color: COLORS.brand170 },
  { line: "}", color: COLORS.pine70 },
];

export const InterfacesScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const blocks = [
    { title: "Tool", lines: TOOL_INTERFACE, delay: 10 },
    { title: "Channel", lines: CHANNEL_INTERFACE, delay: 25 },
    { title: "LLMProvider", lines: PROVIDER_INTERFACE, delay: 40 },
  ];

  return (
    <AbsoluteFill>
      <Background />
      <AbsoluteFill
        style={{
          padding: "60px 100px",
          flexDirection: "column",
        }}
      >
        <SectionHeader
          title="Interface-Driven Architecture"
          subtitle="Every component is swappable via Go interfaces"
        />
        <div
          style={{
            display: "flex",
            gap: 30,
            flex: 1,
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {blocks.map((block, bi) => {
            const blockEntrance = spring({
              frame: frame - block.delay,
              fps,
              config: { damping: 200 },
            });
            return (
              <div
                key={bi}
                style={{
                  opacity: interpolate(blockEntrance, [0, 1], [0, 1]),
                  transform: `translateY(${interpolate(blockEntrance, [0, 1], [40, 0])}px)`,
                  background: COLORS.navyLight,
                  border: `1px solid ${COLORS.pine70}25`,
                  borderRadius: 14,
                  padding: "24px 28px",
                  minWidth: 380,
                }}
              >
                <div
                  style={{
                    fontSize: 28,
                    color: COLORS.whiteAlpha,
                    fontFamily: FONTS.mono,
                    marginBottom: 16,
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                  }}
                >
                  {block.title}
                </div>
                {block.lines.map((l, li) => {
                  const lineEntrance = spring({
                    frame: frame - (block.delay + 5 + li * 3),
                    fps,
                    config: { damping: 200 },
                  });
                  return (
                    <div
                      key={li}
                      style={{
                        opacity: interpolate(lineEntrance, [0, 1], [0, 1]),
                        fontSize: 32,
                        color: l.color,
                        fontFamily: FONTS.mono,
                        lineHeight: 1.8,
                        whiteSpace: "pre",
                      }}
                    >
                      {l.line}
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
