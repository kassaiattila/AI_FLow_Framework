import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Allow large file uploads (PDF folder upload)
  serverExternalPackages: [],
  experimental: {
    serverActions: {
      bodySizeLimit: "100mb",
    },
  },
};

export default nextConfig;
