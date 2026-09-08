// Oracle official brand palette
// Source: Oracle Theme Colors text usage guidelines
export const COLORS = {
  // === Dark background palette (Slate 170 base) ===
  navy: "#2A2F2F",                            // Slate 170 (primary dark bg)
  navyLight: "#3C4545",                       // Slate 150 (elevated surfaces)
  darkBg: "#1E2323",                          // Deep slate (deepest bg)

  // === Text colors ===
  white: "#FBF9F8",                           // Neutral 10 (primary text on dark)
  whiteAlpha: "rgba(251, 249, 248, 0.7)",     // Neutral 10 @ 70%

  // === Oracle brand ===
  oracleRed: "#C74634",                       // Oracle Red (primary brand)
  oracleRedGlow: "rgba(199, 70, 52, 0.25)",   // Oracle Red glow

  // === Dark bg accent palette (from guidelines_1) ===
  brand170: "#F0CC72",                        // Brand 170 (gold)
  pine70: "#608596",                          // Pine 70 (steel blue)
  teal70: "#89B280",                          // Teal 70 (sage green)

  // === Light bg accent palette ===
  sky140: "#04156F",                          // Sky 140 (deep navy)
  rose140: "#6C3F49",                         // Rose 140 (muted burgundy)

  // === Glow effects ===
  blueGlow: "rgba(96, 133, 150, 0.25)",       // Pine 70 glow
  limeGlow: "rgba(240, 204, 114, 0.2)",       // Brand 170 gold glow
  oracleRedGlowStrong: "rgba(199, 70, 52, 0.4)", // Oracle Red strong glow

  // === Backward-compat aliases (scenes reference these) ===
  electricBlue: "#608596",                    // → Pine 70
  lime: "#F0CC72",                            // → Brand 170
} as const;

export const FONTS = {
  heading: "Inter",
  mono: "Space Mono",
} as const;

export const VIDEO = {
  width: 1920,
  height: 1080,
  fps: 30,
} as const;

// Scene durations in frames (at 30fps)
export const SCENE_FRAMES = {
  title: 180,           // 6s
  numbers: 180,         // 6s
  whyOracle: 180,       // 6s
  architecture: 180,    // 6s
  agentLoop: 180,       // 6s
  channels: 150,        // 5s
  tools: 150,           // 5s
  hardwareTools: 180,   // 6s
  providers: 150,       // 5s
  oracle: 210,          // 7s
  vectorSearch: 180,    // 6s
  oracleConfig: 150,    // 5s
  skillsSecurity: 180,  // 6s
  interfaces: 180,      // 6s
  quickstart: 180,      // 6s
  cliCommands: 150,     // 5s
  inspect: 150,         // 5s
  docker: 150,          // 5s
  oracleCloud: 180,     // 6s
  deploy: 150,          // 5s
  embeddedTargets: 150, // 5s
  voiceCron: 150,       // 5s
  unique: 150,          // 5s
  sisterProjects: 150,  // 5s
  outro: 150,           // 5s
} as const;

export const TRANSITION_FRAMES = 15;
