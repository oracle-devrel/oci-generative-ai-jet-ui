import type { NextConfig } from "next";

const isProd = process.env.NODE_ENV === "production";

const nextConfig: NextConfig = {
  output: "export",
  basePath: isProd ? "/agent-reasoning" : "",
  assetPrefix: isProd ? "/agent-reasoning/" : "",
  images: { unoptimized: true },
};

export default nextConfig;
