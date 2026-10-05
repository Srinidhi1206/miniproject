import type { NextConfig } from "next";

// NEXT_PUBLIC_* values are inlined into the browser bundle at BUILD time. If the
// API URL is missing on Vercel, the app would silently fall back to
// http://localhost:8000 — which works on a developer's laptop and nowhere else.
// Fail the deployment loudly instead of shipping a site that can't reach its API.
const apiUrl = process.env.NEXT_PUBLIC_API_URL?.trim();
if (process.env.VERCEL === "1") {
  if (!apiUrl) {
    throw new Error(
      "NEXT_PUBLIC_API_URL is not set for this Vercel build. Set it to the deployed FastAPI " +
        "backend (e.g. https://sentinel-api.onrender.com) in Project → Settings → Environment Variables, then redeploy.",
    );
  }
  if (/localhost|127\.0\.0\.1/.test(apiUrl)) {
    throw new Error(`NEXT_PUBLIC_API_URL points to ${apiUrl}, which browsers can't reach in production.`);
  }
}

const nextConfig: NextConfig = {
  output: "standalone", // small self-contained server for the Docker image
  poweredByHeader: false,
  async headers() {
    return [{
      source: "/:path*",
      headers: [
        { key: "X-Content-Type-Options", value: "nosniff" },
        { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
        { key: "X-Frame-Options", value: "DENY" },
        { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
      ],
    }];
  },
};

export default nextConfig;
