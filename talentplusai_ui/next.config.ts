import type { NextConfig } from "next";

/**
 * API requests are proxied by `src/app/api/[[...path]]/route.ts` (Node) to Django.
 * Do not duplicate rewrites here — they can cause confusing "Failed to proxy" logs and
 * double-handling. Set NEXT_PUBLIC_API_URL in .env.local to match manage.py (e.g. http://127.0.0.1:8000).
 */
const nextConfig: NextConfig = {};

export default nextConfig;
