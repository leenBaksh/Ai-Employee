import { NextRequest, NextResponse } from 'next/server'

// Paths that never require auth
const PUBLIC_PATHS = ['/login', '/api/auth/login', '/api/auth/logout']
const NEXT_INTERNAL = ['/_next/', '/favicon.ico']

// Web Crypto API — works in the Edge Runtime (no Node.js crypto needed)
async function computeToken(): Promise<string> {
  const secret   = process.env.SESSION_SECRET   ?? 'fallback-secret'
  const password = process.env.DASHBOARD_PASSWORD ?? 'changeme'

  const enc     = new TextEncoder()
  const keyData = enc.encode(secret)
  const msgData = enc.encode(password)

  const key = await crypto.subtle.importKey(
    'raw',
    keyData,
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign'],
  )

  const sig   = await crypto.subtle.sign('HMAC', key, msgData)
  const bytes = Array.from(new Uint8Array(sig))
  return bytes.map(b => b.toString(16).padStart(2, '0')).join('')
}

function isPublic(pathname: string): boolean {
  if (NEXT_INTERNAL.some(p => pathname.startsWith(p))) return true
  if (PUBLIC_PATHS.some(p => pathname === p || pathname.startsWith(p + '/'))) return true
  return false
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  if (isPublic(pathname)) {
    return NextResponse.next()
  }

  const sessionCookie = request.cookies.get('ai_session')?.value
  const expected      = await computeToken()

  if (sessionCookie === expected) {
    return NextResponse.next()
  }

  // API calls (non-HTML or /api/* paths) → 401 JSON
  const accept    = request.headers.get('accept') ?? ''
  const isApiCall =
    pathname.startsWith('/api/') ||
    (!accept.includes('text/html') && !accept.includes('*/*'))

  if (isApiCall) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  // Page request → redirect to login
  const loginUrl = new URL('/login', request.url)
  loginUrl.searchParams.set('next', pathname)
  return NextResponse.redirect(loginUrl)
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
}
