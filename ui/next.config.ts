import type { NextConfig } from "next";

const apiBase =
  process.env.NEXT_PUBLIC_MIRAGE_API_BASE_URL ??
  process.env.MIRAGE_API_BASE_URL ??
  "http://127.0.0.1:5100";

const nextConfig: NextConfig = {
  async rewrites() {
    if (process.env.NODE_ENV !== "development") {
      return [];
    }

    return [
      {
        source: "/api/:path*",
        destination: `${apiBase}/api/:path*`,
      },
      {
        source: "/assets/:path*",
        destination: `${apiBase}/assets/:path*`,
      },
    ];
  },
};

export default nextConfig;
