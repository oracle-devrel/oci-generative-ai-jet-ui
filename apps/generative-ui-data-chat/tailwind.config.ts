import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"]
      },
      colors: {
        ink: "#151515",
        paper: "#f7f4ef",
        signal: "#c74634",
        ocean: "#0f766e",
        cobalt: "#2563eb",
        moss: "#52734d"
      }
    }
  },
  plugins: []
};

export default config;
