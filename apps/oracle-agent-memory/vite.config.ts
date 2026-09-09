import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

// __dirname isn't defined in ESM; derive it from import.meta.url
const __dirname = dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react()],
  root: 'src/client',
  resolve: {
    alias: {
      '@shared': resolve(__dirname, 'shared'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      // Note the trailing slash. Without it, this also matches `/api.ts`
      // (the client-side module), which then 404s through the proxy and
      // breaks the React app load.
      '/api/': 'http://localhost:3001',
    },
  },
  build: {
    outDir: '../../dist/client',
    emptyOutDir: true,
  },
});
