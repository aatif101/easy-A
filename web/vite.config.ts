import react from "@vitejs/plugin-react";
import { loadEnv, type Plugin } from "vite";
import { defineConfig } from "vitest/config";

// Optional dev-only proxy: EASY_A_DEV_PROXY=https://easy-a-api.onrender.com forwards /api to the
// hosted API, whose CORS policy only admits the deployed site. Pair it with
// VITE_API_BASE_URL=http://localhost:5173. Production builds ignore it.
const devProxy = process.env.EASY_A_DEV_PROXY;

// Cloudflare Web Analytics (cookie-free visitor counts). The beacon is added to index.html only
// when VITE_CF_ANALYTICS_TOKEN is set at build time, which is only on the hosted easy-a-web
// service, so local dev and CI builds send nothing.
function cloudflareWebAnalytics(token: string | undefined): Plugin {
  return {
    name: "cloudflare-web-analytics",
    apply: "build",
    transformIndexHtml() {
      const trimmed = token?.trim();
      if (!trimmed) return [];
      if (!/^[0-9a-f]{32}$/i.test(trimmed)) {
        throw new Error("VITE_CF_ANALYTICS_TOKEN must be the 32-character hex token from Cloudflare");
      }
      return [
        {
          tag: "script",
          attrs: {
            defer: true,
            src: "https://static.cloudflareinsights.com/beacon.min.js",
            "data-cf-beacon": JSON.stringify({ token: trimmed }),
          },
          injectTo: "body",
        },
      ];
    },
  };
}

export default defineConfig(({ mode }) => ({
  plugins: [
    react(),
    cloudflareWebAnalytics(loadEnv(mode, process.cwd(), "VITE_").VITE_CF_ANALYTICS_TOKEN),
  ],
  server: devProxy
    ? { proxy: { "/api": { target: devProxy, changeOrigin: true } } }
    : undefined,
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    css: true,
  },
}));
