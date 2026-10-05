import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// Optional dev-only proxy: EASY_A_DEV_PROXY=https://easy-a-api.onrender.com forwards /api to the
// hosted API, whose CORS policy only admits the deployed site. Pair it with
// VITE_API_BASE_URL=http://localhost:5173. Production builds ignore it.
const devProxy = process.env.EASY_A_DEV_PROXY;

export default defineConfig({
  plugins: [react()],
  server: devProxy
    ? { proxy: { "/api": { target: devProxy, changeOrigin: true } } }
    : undefined,
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    css: true,
  },
});
