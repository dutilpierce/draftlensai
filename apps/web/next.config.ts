import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  /** Explicit default: URLs in sitemap and canonicals omit trailing slashes. */
  trailingSlash: false,
};

export default nextConfig;
