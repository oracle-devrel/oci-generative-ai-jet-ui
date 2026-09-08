import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";
import { Background } from "../components/Background";
import { SectionHeader } from "../components/SectionHeader";
import { COLORS, FONTS } from "../theme";

const I2C_ITEMS = [
  "Temperature sensors",
  "Humidity sensors",
  "Pressure sensors",
  "OLED displays",
  "Motor controllers",
  "Register read/write",
];

const SPI_ITEMS = [
  "ADC/DAC converters",
  "SD card access",
  "TFT displays",
  "Robotics actuators",
  "Sensor arrays",
  "Flash memory",
];

export const HardwareToolsScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

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
          title="Hardware Tools"
          subtitle="Talk to physical devices over I2C and SPI buses"
        />
        <div
          style={{
            display: "flex",
            gap: 60,
            flex: 1,
            justifyContent: "center",
            alignItems: "center",
          }}
        >
          {/* I2C Column */}
          <div style={{ flex: 1, maxWidth: 500 }}>
            {(() => {
              const headerEntrance = spring({
                frame: frame - 10,
                fps,
                config: { damping: 200 },
              });
              return (
                <div
                  style={{
                    opacity: interpolate(headerEntrance, [0, 1], [0, 1]),
                    fontSize: 64,
                    fontWeight: 800,
                    color: COLORS.pine70,
                    fontFamily: FONTS.heading,
                    marginBottom: 24,
                    display: "flex",
                    alignItems: "center",
                    gap: 12,
                  }}
                >
                  <span style={{ fontSize: 72 }}>🔌</span> I2C Bus
                </div>
              );
            })()}
            {I2C_ITEMS.map((item, i) => {
              const entrance = spring({
                frame: frame - (20 + i * 5),
                fps,
                config: { damping: 200 },
              });
              return (
                <div
                  key={i}
                  style={{
                    opacity: interpolate(entrance, [0, 1], [0, 1]),
                    transform: `translateX(${interpolate(entrance, [0, 1], [-40, 0])}px)`,
                    display: "flex",
                    alignItems: "center",
                    gap: 12,
                    padding: "12px 0",
                    borderBottom: `1px solid ${COLORS.pine70}15`,
                  }}
                >
                  <div
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: "50%",
                      backgroundColor: COLORS.pine70,
                      flexShrink: 0,
                    }}
                  />
                  <span
                    style={{
                      fontSize: 36,
                      color: COLORS.white,
                      fontFamily: FONTS.mono,
                    }}
                  >
                    {item}
                  </span>
                </div>
              );
            })}
          </div>

          {/* Divider */}
          {(() => {
            const divEntrance = spring({
              frame: frame - 15,
              fps,
              config: { damping: 200 },
            });
            return (
              <div
                style={{
                  width: 2,
                  height: interpolate(divEntrance, [0, 1], [0, 380]),
                  background: `linear-gradient(180deg, ${COLORS.pine70}, ${COLORS.teal70})`,
                  opacity: 0.4,
                }}
              />
            );
          })()}

          {/* SPI Column */}
          <div style={{ flex: 1, maxWidth: 500 }}>
            {(() => {
              const headerEntrance = spring({
                frame: frame - 15,
                fps,
                config: { damping: 200 },
              });
              return (
                <div
                  style={{
                    opacity: interpolate(headerEntrance, [0, 1], [0, 1]),
                    fontSize: 64,
                    fontWeight: 800,
                    color: COLORS.teal70,
                    fontFamily: FONTS.heading,
                    marginBottom: 24,
                    display: "flex",
                    alignItems: "center",
                    gap: 12,
                  }}
                >
                  <span style={{ fontSize: 72 }}>📡</span> SPI Bus
                </div>
              );
            })()}
            {SPI_ITEMS.map((item, i) => {
              const entrance = spring({
                frame: frame - (25 + i * 5),
                fps,
                config: { damping: 200 },
              });
              return (
                <div
                  key={i}
                  style={{
                    opacity: interpolate(entrance, [0, 1], [0, 1]),
                    transform: `translateX(${interpolate(entrance, [0, 1], [40, 0])}px)`,
                    display: "flex",
                    alignItems: "center",
                    gap: 12,
                    padding: "12px 0",
                    borderBottom: `1px solid ${COLORS.teal70}15`,
                  }}
                >
                  <div
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: "50%",
                      backgroundColor: COLORS.teal70,
                      flexShrink: 0,
                    }}
                  />
                  <span
                    style={{
                      fontSize: 36,
                      color: COLORS.white,
                      fontFamily: FONTS.mono,
                    }}
                  >
                    {item}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
