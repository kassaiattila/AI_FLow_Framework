import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig(({ mode }) => ({
  plugins: [react(), tailwindcss()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      // All API traffic goes directly to FastAPI — no Next.js needed
      "/api": {
        target: "http://localhost:8102",
        changeOrigin: true,
        // Disable buffering for SSE (process-stream) endpoints
        configure: (proxy) => {
          proxy.on("proxyRes", (proxyRes) => {
            if (proxyRes.headers["content-type"]?.includes("text/event-stream")) {
              // Prevent proxy from buffering SSE chunks
              proxyRes.headers["cache-control"] = "no-cache";
              proxyRes.headers["x-accel-buffering"] = "no";
            }
          });
        },
      },
      "/health": {
        target: "http://localhost:8102",
        changeOrigin: true,
      },
    },
  },
  build: {
    sourcemap: mode === "development",
  },
  base: "./",
}));
