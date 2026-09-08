import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      "/chat": "http://localhost:8000",
      "/migrate": "http://localhost:8000",
      "/stats": "http://localhost:8000",
      "/inspect": "http://localhost:8000",
      "/source": "http://localhost:8000",
      "/assess": "http://localhost:8000",
      "/memory": "http://localhost:8000",
      "/reset": "http://localhost:8000",
    },
  },
});
