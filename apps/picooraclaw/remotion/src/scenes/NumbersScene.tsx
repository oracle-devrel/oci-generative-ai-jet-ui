import React from "react";
import { AbsoluteFill, useVideoConfig } from "remotion";
import { Background } from "../components/Background";
import { SectionHeader } from "../components/SectionHeader";
import { MetricCounter } from "../components/MetricCounter";
import { COLORS } from "../theme";

export const NumbersScene: React.FC = () => {
  const { fps } = useVideoConfig();

  const metrics = [
    { value: "$10", label: "Hardware Cost", numericValue: 10, prefix: "$", suffix: "" },
    { value: "10", label: "MB RAM", numericValue: 10, prefix: "", suffix: "MB" },
    { value: "1", label: "Second Boot", numericValue: 1, prefix: "", suffix: "s" },
    { value: "23", label: "Packages", numericValue: 23, prefix: "", suffix: "" },
  ];

  return (
    <AbsoluteFill>
      <Background />
      <AbsoluteFill
        style={{
          padding: "80px 120px",
          flexDirection: "column",
          justifyContent: "center",
        }}
      >
        <SectionHeader
          title="By The Numbers"
          subtitle="Built for resource-constrained environments"
          accent={COLORS.brand170}
        />
        <div
          style={{
            display: "flex",
            justifyContent: "space-around",
            alignItems: "center",
            flex: 1,
            maxWidth: 1400,
            margin: "0 auto",
          }}
        >
          {metrics.map((m, i) => (
            <MetricCounter
              key={i}
              value={m.value}
              label={m.label}
              numericValue={m.numericValue}
              prefix={m.prefix}
              suffix={m.suffix}
              delay={Math.round(0.8 * fps + i * 8)}
              color={i % 2 === 0 ? COLORS.brand170 : COLORS.teal70}
            />
          ))}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
