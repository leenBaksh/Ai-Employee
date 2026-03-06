import { NextRequest, NextResponse } from 'next/server'
import { createHmac } from 'crypto'

// ── Auth ──────────────────────────────────────────────────────────────────────

function computeToken(): string {
  const secret = process.env.SESSION_SECRET ?? 'fallback-secret'
  const password = process.env.DASHBOARD_PASSWORD ?? 'changeme'
  return createHmac('sha256', secret).update(password).digest('hex')
}

function isAuthorized(request: NextRequest): boolean {
  const sessionCookie = request.cookies.get('ai_session')?.value
  return sessionCookie === computeToken()
}

// ── Vault Context ─────────────────────────────────────────────────────────────

interface VaultContext {
  stats: Record<string, number>
  tasks: Array<{ filename: string; type: string; age_human: string }>
  logs: Array<{ timestamp: string; action_type: string; actor: string; target: string; result: string }>
}

async function fetchVaultContext(): Promise<VaultContext> {
  const base = 'http://localhost:8888'
  try {
    const [stats, tasks, logs] = await Promise.all([
      fetch(`${base}/api/stats`).then(r => r.json()).catch(() => ({})),
      fetch(`${base}/api/tasks`).then(r => r.json()).catch(() => []),
      fetch(`${base}/api/logs?limit=10`).then(r => r.json()).catch(() => []),
    ])
    return { stats, tasks, logs }
  } catch {
    return { stats: {}, tasks: [], logs: [] }
  }
}

function buildSystemPrompt(ctx: VaultContext): string {
  const { stats, tasks, logs } = ctx
  const timestamp = new Date().toISOString()

  const taskList = tasks.length > 0
    ? tasks.slice(0, 10).map(t => `  - ${t.filename} (${t.type}, ${t.age_human})`).join('\n')
    : '  (none)'

  const recentLogs = logs.length > 0
    ? logs.slice(0, 8).map(l => `  - [${l.timestamp}] ${l.action_type}: ${l.target} → ${l.result}`).join('\n')
    : '  (none)'

  return `You are the AI Employee assistant for World Digital.
You help the business owner understand what's happening in their AI Employee system.

Current vault state (as of ${timestamp}):
- Needs Action: ${stats.needs_action ?? 0} tasks
- Pending Approval: ${stats.pending_approval ?? 0} items
- Done: ${stats.done ?? 0} completed tasks
- SLA Breaches: ${stats.sla_breaches ?? 0}
- Drafts: ${stats.drafts ?? 0}
- In Progress (local): ${stats.in_progress_local ?? 0}
- In Progress (cloud): ${stats.in_progress_cloud ?? 0}

Recent tasks requiring action:
${taskList}

Recent activity log:
${recentLogs}

Answer questions about tasks, emails, system health, and business operations.
Keep responses concise and actionable. Use markdown formatting for clarity.`
}

// ── Route Handler ─────────────────────────────────────────────────────────────

export const runtime = 'nodejs'

export async function POST(request: NextRequest) {
  if (!isAuthorized(request)) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const apiKey = process.env.OPENROUTER_API_KEY
  const baseUrl = process.env.BASE_URL ?? 'https://openrouter.ai/api/v1/chat/completions'
  const model = process.env.CLAUDE_MODEL ?? 'claude-sonnet-4-20250514'

  if (!apiKey) {
    return NextResponse.json(
      { error: 'OPENROUTER_API_KEY not configured in .env.local' },
      { status: 500 },
    )
  }

  let body: { messages?: Array<{ role: string; content: string }> }
  try {
    body = await request.json()
  } catch {
    return NextResponse.json({ error: 'Invalid request body' }, { status: 400 })
  }

  const messages = body.messages ?? []
  if (messages.length === 0) {
    return NextResponse.json({ error: 'No messages provided' }, { status: 400 })
  }

  const ctx = await fetchVaultContext()
  const systemPrompt = buildSystemPrompt(ctx)

  // Call OpenRouter (OpenAI-compatible) with streaming
  let upstream: Response
  try {
    upstream = await fetch(baseUrl, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
        'HTTP-Referer': 'http://localhost:3000',
        'X-Title': 'AI Employee Dashboard',
      },
      body: JSON.stringify({
        model,
        stream: true,
        max_tokens: 1024,
        messages: [
          { role: 'system', content: systemPrompt },
          ...messages.map(m => ({ role: m.role, content: m.content })),
        ],
      }),
      signal: AbortSignal.timeout(60_000),
    })
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    return NextResponse.json({ error: `Cannot reach OpenRouter: ${msg}` }, { status: 502 })
  }

  if (!upstream.ok) {
    const err = await upstream.text()
    return NextResponse.json({ error: `Upstream error: ${err}` }, { status: upstream.status })
  }

  // Parse SSE from OpenRouter and re-stream plain text to the client
  const stream = new ReadableStream({
    async start(controller) {
      const enc = new TextEncoder()
      const reader = upstream.body!.getReader()
      const dec = new TextDecoder()
      let buffer = ''

      try {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += dec.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() ?? ''  // keep incomplete last line

          for (const line of lines) {
            const trimmed = line.trim()
            if (!trimmed.startsWith('data:')) continue
            const data = trimmed.slice(5).trim()
            if (data === '[DONE]') continue

            try {
              const json = JSON.parse(data)
              const delta = json.choices?.[0]?.delta?.content
              if (delta) controller.enqueue(enc.encode(delta))
            } catch {
              // malformed chunk — skip
            }
          }
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Unknown error'
        controller.enqueue(enc.encode(`\n\n[Error: ${msg}]`))
      } finally {
        controller.close()
      }
    },
  })

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/plain; charset=utf-8',
      'Transfer-Encoding': 'chunked',
      'X-Content-Type-Options': 'nosniff',
    },
  })
}
