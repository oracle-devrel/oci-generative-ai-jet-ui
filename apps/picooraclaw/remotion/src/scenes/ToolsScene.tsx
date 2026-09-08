import React from "react";
import { AbsoluteFill } from "remotion";
import { Background } from "../components/Background";
import { SectionHeader } from "../components/SectionHeader";
import { FeatureGrid } from "../components/FeatureCard";
import { COLORS } from "../theme";

const TOOLS = [
  { icon: "📁", title: "Filesystem" },
  { icon: "🐚", title: "Shell" },
  { icon: "🌐", title: "Web Search" },
  { icon: "✏️", title: "Edit" },
  { icon: "🔀", title: "Spawn" },
  { icon: "⏰", title: "Cron" },
  { icon: "🧠", title: "Remember" },
  { icon: "🔍", title: "Recall" },
  { icon: "📨", title: "Message" },
  { icon: "🔌", title: "I2C" },
  { icon: "📡", title: "SPI" },
  { icon: "💾", title: "State" },
  { icon: "📊", title: "Analyze" },
  { icon: "🔗", title: "HTTP" },
  { icon: "🛠️", title: "Skills" },
];

export const ToolsScene: React.FC = () => {
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
          title="15 Built-in Tools"
          subtitle="From filesystem ops to hardware I2C/SPI"
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
            items={TOOLS}
            columns={5}
            staggerDelay={3}
            baseDelay={15}
            accentColor={COLORS.teal70}
            small
          />
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
