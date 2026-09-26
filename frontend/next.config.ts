import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Don't advertise the framework to fingerprinting scanners.
  poweredByHeader: false,
  // Product/receipt images are served by Django in dev.
  images: {
    remotePatterns: [
      { protocol: "http", hostname: "localhost", port: "8020" },
    ],
  },
};

export default nextConfig;
