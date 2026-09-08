/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Theme-aware neutrals — back the CSS variables in styles.css.
        bg: {
          base: "var(--bg-base)",
          panel: "var(--bg-panel)",
          elev: "var(--bg-elev)",
          hover: "var(--bg-hover)",
        },
        text: {
          primary: "var(--text-primary)",
          accent: "var(--text-accent)",
          secondary: "var(--text-secondary)",
          muted: "var(--text-muted)",
        },
        border: {
          subtle: "var(--border-subtle)",
          medium: "var(--border-medium)",
        },
        overlay: {
          soft: "var(--overlay-soft)",
          medium: "var(--overlay-medium)",
          strong: "var(--overlay-strong)",
        },
        // Accent colors — same semantic meaning in light + dark.
        accent: {
          oracle: "#f80000",
          tool: "#ffd166",
          memory: "#06d6a0",
          skill: "#118ab2",
          sql: "#ef476f",
        },
      },
      fontFamily: {
        sans: ["-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "sans-serif"],
        mono: ["JetBrains Mono", "Menlo", "Monaco", "Consolas", "monospace"],
      },
      keyframes: {
        "pulse-glow-store": {
          "0%": {
            boxShadow: "inset 0 0 0 0 rgba(6, 214, 160, 0.0)",
            backgroundColor: "rgba(6, 214, 160, 0.18)",
          },
          "100%": {
            boxShadow: "inset 0 0 0 999px rgba(6, 214, 160, 0.0)",
            backgroundColor: "transparent",
          },
        },
      },
      animation: {
        "pulse-store": "pulse-glow-store 3.5s ease-out",
      },
    },
  },
  plugins: [],
};
