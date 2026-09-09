import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Built assets are served from "/" by FastAPI (StaticFiles mount), so use
// relative asset paths (base: "./"). The dev proxy forwards the agent API
// to the running uvicorn instance for hot-reload development; the deliverable
// is the production build in dist/.
export default defineConfig({
  base: "./",
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      "/chat": "http://127.0.0.1:8000",
      "/predict": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
      "/memory": "http://127.0.0.1:8000",
    },
  },
});
