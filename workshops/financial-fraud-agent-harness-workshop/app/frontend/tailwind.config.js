/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: {
          base: "#0a0a0a",
          panel: "#121212",
          elev: "#1a1a1a",
        },
        text: {
          primary: "#f5f5f5",
          accent: "#e0e0e0",
          secondary: "#888",
          muted: "#555",
        },
        accent: {
          oracle: "#f80000",
          tool: "#ffd166",
          memory: "#06d6a0",
          skill: "#118ab2",
          sql: "#ef476f",
        },
      },
      fontFamily: {
        mono: ["JetBrains Mono", "Menlo", "Monaco", "Consolas", "monospace"],
      },
    },
  },
  plugins: [],
};
