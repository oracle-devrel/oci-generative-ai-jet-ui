import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// We bind to 0.0.0.0 and allow any host because in Codespaces (and similar dev
// tunnels) the request reaches Vite with a Host header like
// `verbose-potato-…-3000.app.github.dev`. Vite 6's default `allowedHosts` only
// permits localhost/127.0.0.1 and blocks anything else with a 403, which the
// Codespaces proxy surfaces as `HTTP 502`. Setting `allowedHosts: true`
// disables that check — fine for a workshop dev environment.
//
// HMR over the dev tunnel needs `clientPort: 443` so the browser-side
// WebSocket targets the public HTTPS port instead of `ws://localhost:3000`.
export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 3000,
    strictPort: true,
    allowedHosts: true,
    hmr: {
      clientPort: 443,
    },
    proxy: {
      "/api": "http://localhost:8000",
      "/socket.io": { target: "http://localhost:8000", ws: true },
    },
  },
});
