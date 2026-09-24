/** @type {import('next').NextConfig} */

// Hosted-demo mode: when DEMO_BACKEND_URL is set (see render.yaml), the Next
// server proxies /api/* to the backend service so the browser only ever talks
// to one origin (no CORS, and report/CSV downloads work unchanged). Unset in
// local development, where the frontend calls the backend directly.
const demoBackend = process.env.DEMO_BACKEND_URL
  ? process.env.DEMO_BACKEND_URL.includes("://")
    ? process.env.DEMO_BACKEND_URL
    : `https://${process.env.DEMO_BACKEND_URL}`
  : null;

const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return demoBackend
      ? [{ source: "/api/:path*", destination: `${demoBackend}/api/:path*` }]
      : [];
  },
};

export default nextConfig;
