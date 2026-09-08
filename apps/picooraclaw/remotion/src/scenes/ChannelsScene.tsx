import React from "react";
import { AbsoluteFill } from "remotion";
import { Background } from "../components/Background";
import { SectionHeader } from "../components/SectionHeader";
import { FeatureGrid } from "../components/FeatureCard";
import { COLORS } from "../theme";

const CHANNELS = [
  { icon: "📱", title: "Telegram" },
  { icon: "🎮", title: "Discord" },
  { icon: "💼", title: "Slack" },
  { icon: "💬", title: "DingTalk" },
  { icon: "📩", title: "LINE" },
  { icon: "🐦", title: "Feishu" },
  { icon: "🐧", title: "QQ" },
  { icon: "📲", title: "WhatsApp" },
  { icon: "📷", title: "MaixCAM" },
  { icon: "🤖", title: "OneBot" },
];

export const ChannelsScene: React.FC = () => {
  return (
    <AbsoluteFill>
      <Background />
      <AbsoluteFill
        style={{
          padding: "60px 100px",
          flexDirection: "column",
          justifyContent: "center",
        }}
      >
        <SectionHeader
          title="10 Input Channels"
          subtitle="Connect from anywhere"
          accent={COLORS.teal70}
        />
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            flex: 1,
            alignItems: "center",
          }}
        >
          <FeatureGrid
            items={CHANNELS}
            columns={5}
            staggerDelay={4}
            baseDelay={15}
            accentColor={COLORS.pine70}
          />
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
