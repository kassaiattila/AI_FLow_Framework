import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
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
