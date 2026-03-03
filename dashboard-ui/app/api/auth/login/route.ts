import { NextRequest, NextResponse } from 'next/server'
import { createHmac } from 'crypto'

function computeToken(): string {
  const secret = process.env.SESSION_SECRET ?? 'fallback-secret'
  const password = process.env.DASHBOARD_PASSWORD ?? 'changeme'
  return createHmac('sha256', secret).update(password).digest('hex')
}

export async function POST(request: NextRequest) {
  let body: { password?: string }
  try {
    body = await request.json()
  } catch {
    return NextResponse.json({ error: 'Invalid request body' }, { status: 400 })
  }

  const { password } = body
  const expected = process.env.DASHBOARD_PASSWORD ?? 'changeme'

  if (!password || password !== expected) {
    return NextResponse.json({ error: 'Incorrect password' }, { status: 401 })
  }

  const token = computeToken()
  const response = NextResponse.json({ ok: true })
  response.cookies.set('ai_session', token, {
    httpOnly: true,
    sameSite: 'lax',
    path: '/',
    // 7-day session
    maxAge: 60 * 60 * 24 * 7,
  })
  return response
}
