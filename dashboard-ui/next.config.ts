import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  // Allow cross-origin requests from WSL2 host IP (Windows browser → WSL2 dev server)
  allowedDevOrigins: ['172.29.54.28', '172.29.0.0/16', '192.168.0.0/16'],

  // Proxy /api/* to Flask backend on :8888.
  // /api/auth/* is intentionally excluded — served by Next.js route handlers.
  async rewrites() {
    return {
      beforeFiles: [],
      afterFiles: [
        {
          // Match /api/* but NOT /api/auth/* or /api/assistant (handled by Next.js)
          source: '/api/:path((?!auth(?:/|$)|assistant(?:/|$)).*)',
          destination: 'http://localhost:8888/api/:path*',
        },
      ],
      fallback: [],
    }
  },
}

export default nextConfig
