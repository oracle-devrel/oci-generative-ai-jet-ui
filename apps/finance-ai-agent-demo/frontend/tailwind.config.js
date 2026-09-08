/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: "#0A0A0A",
        secondary: "#111111",
        tertiary: "#1A1A1A",
        "text-primary": "#E5E5E5",
        "text-secondary": "#999999",
        "text-accent": "#C0C0C0",
        "accent-vector": "#7C3AED",
        "accent-sql": "#2563EB",
        "accent-graph": "#059669",
        "accent-hybrid": "#D97706",
        "accent-json": "#DC2626",
        "accent-text": "#6B7280",
        "accent-spatial": "#0EA5E9",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      animation: {
        "pulse-glow": "pulseGlow 2s ease-in-out infinite",
        "slide-in": "slideIn 0.3s ease-out",
      },
      keyframes: {
        pulseGlow: {
          "0%, 100%": { boxShadow: "0 0 15px rgba(192,192,192,0.05)" },
          "50%": { boxShadow: "0 0 25px rgba(192,192,192,0.15)" },
        },
        slideIn: {
          "0%": { opacity: "0", transform: "translateY(-10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};
