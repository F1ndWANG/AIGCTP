/** @type {import('next').NextConfig} */
const API_URL = process.env.API_URL || "http://127.0.0.1:9000";

const withSerwist = require("@serwist/next").default({
  swSrc: "sw/worker.ts",
  swDest: "public/sw.js",
});

const nextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${API_URL}/api/v1/:path*`,
      },
      {
        source: "/health/:path*",
        destination: `${API_URL}/health/:path*`,
      },
    ];
  },
};

module.exports = withSerwist(nextConfig);
