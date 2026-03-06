import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
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
