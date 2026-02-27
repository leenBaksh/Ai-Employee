import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  // Proxy all /api/* calls to the Flask backend on :8888
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8888/api/:path*',
      },
    ]
  },
}

export default nextConfig
