import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      // FastAPI direct — CRUD routes (no Next.js middleman)
      "/api/v1": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/health": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      // Next.js — subprocess routes (upload, process, generate) + fallback
      "/api": {
        target: "http://localhost:3000",
        changeOrigin: false,
        cookieDomainRewrite: "",
        cookiePathRewrite: "/",
      },
      "/images": {
        target: "http://localhost:3000",
        changeOrigin: false,
      },
    },
  },
  build: {
    sourcemap: mode === "development",
  },
  base: "./",
}));
