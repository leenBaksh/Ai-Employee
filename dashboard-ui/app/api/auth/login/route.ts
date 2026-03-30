import { NextResponse } from 'next/server'

export async function POST(request: Request) {
  try {
    const { password } = await request.json()
    const correctPassword = process.env.DASHBOARD_PASSWORD || 'changeme'

    if (password === correctPassword) {
      // Create session cookie
      const sessionSecret = process.env.SESSION_SECRET || 'fallback-secret'
      const encoder = new TextEncoder()
      const keyData = encoder.encode(sessionSecret)
      const msgData = encoder.encode(password)
      
      const key = await crypto.subtle.importKey('raw', keyData, { name: 'HMAC', hash: 'SHA-256' }, false, ['sign'])
      const sig = await crypto.subtle.sign('HMAC', key, msgData)
      const sessionToken = Array.from(new Uint8Array(sig)).map(b => b.toString(16).padStart(2, '0')).join('')

      const response = NextResponse.json({ success: true })
      response.cookies.set('ai_session', sessionToken, {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'lax',
        maxAge: 60 * 60 * 24 * 7, // 7 days
        path: '/',
      })
      return response
    } else {
      return NextResponse.json({ error: 'Invalid password' }, { status: 401 })
    }
  } catch {
    return NextResponse.json({ error: 'Authentication failed' }, { status: 500 })
  }
}
