'use client'

import { useState, useEffect, FormEvent } from 'react'

interface GmailMessage {
  file: string
  from: string
  subject: string
  received: string
  status: string
}

function StatusBadge({ status }: { status: string }) {
  const done = status === 'Done'
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
      done ? 'bg-green-950 text-green-400' : 'bg-amber-950 text-amber-400'
    }`}>
      {done ? 'Done' : 'Needs Action'}
    </span>
  )
}

export default function GmailPage() {
  const [messages, setMessages] = useState<GmailMessage[]>([])
  const [loading, setLoading]   = useState(true)
  const [to, setTo]             = useState('')
  const [subject, setSubject]   = useState('')
  const [body, setBody]         = useState('')
  const [sending, setSending]   = useState(false)
  const [toast, setToast]       = useState<{ type: 'ok' | 'err'; msg: string } | null>(null)

  const showToast = (type: 'ok' | 'err', msg: string) => {
    setToast({ type, msg })
    setTimeout(() => setToast(null), 4000)
  }

  useEffect(() => {
    fetch('/api/gmail/messages')
      .then(r => r.json())
      .then(d => setMessages(d.messages ?? []))
      .catch(() => showToast('err', 'Failed to load emails'))
      .finally(() => setLoading(false))
  }, [])

  async function handleSend(e: FormEvent) {
    e.preventDefault()
    if (!to.trim() || !subject.trim() || !body.trim()) return
    setSending(true)
    try {
      const res = await fetch('/api/gmail/draft', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ to: to.trim(), subject: subject.trim(), body: body.trim() }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error ?? 'Unknown error')
      showToast('ok', `Draft saved: ${data.draft_file}`)
      setTo('')
      setSubject('')
      setBody('')
    } catch (err: unknown) {
      showToast('err', err instanceof Error ? err.message : 'Draft failed')
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="p-6 max-w-3xl space-y-6">
      {/* Toast */}
      {toast && (
        <div className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-xl text-sm font-medium shadow-xl border
          ${toast.type === 'ok'
            ? 'bg-green-950 text-green-300 border-green-800'
            : 'bg-red-950 text-red-300 border-red-800'}`}
        >
          {toast.type === 'ok' ? '✅' : '❌'} {toast.msg}
        </div>
      )}

      <h1 className="text-lg font-bold text-white">✉️ Gmail</h1>

      {/* Email list */}
      <section>
        <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">Recent Emails</h2>
        {loading ? (
          <div className="text-slate-500 text-sm">Loading…</div>
        ) : messages.length === 0 ? (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-10 text-center">
            <div className="text-4xl mb-2">✉️</div>
            <div className="text-slate-500 text-sm">No email tasks found in vault</div>
          </div>
        ) : (
          <div className="bg-slate-900 border border-slate-800 rounded-xl divide-y divide-slate-800/60 overflow-hidden">
            {messages.map(m => (
              <div key={m.file} className="px-4 py-3">
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="text-white font-medium text-sm truncate">{m.subject || m.file}</span>
                    <StatusBadge status={m.status} />
                  </div>
                  {m.received && (
                    <span className="text-slate-600 text-xs font-mono flex-shrink-0 ml-2">{m.received.slice(0, 16)}</span>
                  )}
                </div>
                <p className="text-slate-500 text-xs">From: {m.from || 'Unknown'}</p>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Compose */}
      <section>
        <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">Compose Draft (requires approval)</h2>
        <form onSubmit={handleSend} className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <div>
            <label className="block text-slate-400 text-xs mb-1.5">To</label>
            <input
              type="email"
              value={to}
              onChange={e => setTo(e.target.value)}
              placeholder="recipient@example.com"
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm placeholder-slate-600 focus:outline-none focus:border-cyan-600"
            />
          </div>
          <div>
            <label className="block text-slate-400 text-xs mb-1.5">Subject</label>
            <input
              type="text"
              value={subject}
              onChange={e => setSubject(e.target.value)}
              placeholder="Email subject"
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm placeholder-slate-600 focus:outline-none focus:border-cyan-600"
            />
          </div>
          <div>
            <label className="block text-slate-400 text-xs mb-1.5">Body</label>
            <textarea
              rows={5}
              value={body}
              onChange={e => setBody(e.target.value)}
              placeholder="Email body…"
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm placeholder-slate-600 focus:outline-none focus:border-cyan-600 resize-none"
            />
          </div>
          <div className="flex items-center justify-between">
            <p className="text-slate-600 text-xs">Saved to /Drafts/ — move to /Approved/ to send</p>
            <button
              type="submit"
              disabled={sending || !to.trim() || !subject.trim() || !body.trim()}
              className="bg-cyan-700 hover:bg-cyan-600 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors"
            >
              {sending ? 'Saving…' : 'Save Draft'}
            </button>
          </div>
        </form>
      </section>
    </div>
  )
}
