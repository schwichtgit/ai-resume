import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import path from 'path';

// https://vitejs.dev/config/
// Where the dev server forwards /api and /mcp. Defaults to a local
// api-service; point it at a deployed host to run the Playwright suite
// against a real backend (and a real LLM) using a locally built frontend,
// which is the only way to exercise a UI change before it ships:
//   VITE_API_PROXY_TARGET=https://frank-ai-resume.schwichtenberg.us npm run dev
const API_PROXY_TARGET =
  process.env.VITE_API_PROXY_TARGET || 'http://localhost:3000';

export default defineConfig(() => ({
  server: {
    host: '::',
    port: 8080,
    hmr: {
      overlay: false,
    },
    proxy: {
      // Proxy API requests to backend during development
      '/api': {
        target: API_PROXY_TARGET,
        changeOrigin: true,
        secure: false,
      },
      '/mcp': {
        target: API_PROXY_TARGET,
        changeOrigin: true,
        secure: false,
      },
    },
  },
  plugins: [tailwindcss(), react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
}));
