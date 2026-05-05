/** @type {import('next').NextConfig} */
const API_URL = process.env.API_URL || "http://localhost:8000";

const withSerwist = require("@serwist/next").default({
  swSrc: "sw/worker.ts",
  swDest: "public/sw.js",
});

const nextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${API_URL}/api/v1/:path*`,
      },
    ];
  },
};

module.exports = withSerwist(nextConfig);
