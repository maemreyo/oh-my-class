import type { NextConfig } from "next";

const nextConfig: NextConfig = {
	// Turbopack is default in Next.js 16 — no config needed
	// Strict mode enabled by default in React 19
	experimental: {
		// Enable Server Actions
		serverActions: {
			bodySizeLimit: "2mb",
		},
	},
};

export default nextConfig;
