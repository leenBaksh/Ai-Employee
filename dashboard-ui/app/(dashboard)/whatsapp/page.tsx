'use client'

import { useState, useEffect, FormEvent } from 'react'

interface WaMessage {
  file: string
  from: string
  message: string
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

type SendMode = 'direct' | 'approval'

export default function WhatsAppPage() {
  const [messages, setMessages] = useState<WaMessage[]>([])
  const [loading, setLoading]   = useState(true)
  const [mode, setMode]         = useState<SendMode>('direct')
  const [toNumber, setToNumber] = useState('')
  const [message, setMessage]   = useState('')
  const [sending, setSending]   = useState(false)
  const [toast, setToast]       = useState<{ type: 'ok' | 'err'; msg: string } | null>(null)

  const showToast = (type: 'ok' | 'err', msg: string) => {
    setToast({ type, msg })
    setTimeout(() => setToast(null), 5000)
  }

  const refreshMessages = () => {
    fetch('/api/whatsapp/messages')
      .then(r => r.json())
      .then(d => setMessages(d.messages ?? []))
      .catch(() => {})
  }

  useEffect(() => {
    fetch('/api/whatsapp/messages')
      .then(r => r.json())
      .then(d => setMessages(d.messages ?? []))
      .catch(() => showToast('err', 'Failed to load messages'))
      .finally(() => setLoading(false))
  }, [])

  async function handleSend(e: FormEvent) {
    e.preventDefault()
    const num = toNumber.trim()
    const msg = message.trim()
    if (!num || !msg) return
    setSending(true)

    const endpoint = mode === 'direct' ? '/api/whatsapp/send' : '/api/whatsapp/draft'
    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ to_number: num, message: msg }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error ?? (data.detail ?? 'Unknown error'))

      if (mode === 'direct') {
        showToast('ok', `✅ Message sent to ${num}`)
        refreshMessages()
      } else {
        showToast('ok', `📋 Queued for approval: ${data.approval_file}`)
      }
      setToNumber('')
      setMessage('')
    } catch (err: unknown) {
      showToast('err', err instanceof Error ? err.message : 'Send failed')
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
          {toast.msg}
        </div>
      )}

      {/* Header */}
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-bold text-white">💬 WhatsApp</h1>
        <span className="text-xs bg-green-950 text-green-400 border border-green-800 px-2 py-0.5 rounded-full font-semibold">
          Meta Cloud API
        </span>
      </div>

      {/* Compose */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">Send Message</h2>
          {/* Mode toggle */}
          <div className="flex rounded-lg overflow-hidden border border-slate-700 text-xs">
            <button
              onClick={() => setMode('direct')}
              className={`px-3 py-1.5 font-semibold transition-colors ${
                mode === 'direct'
                  ? 'bg-green-800 text-green-200'
                  : 'bg-slate-800 text-slate-400 hover:text-white'
              }`}
            >
              Send Now
            </button>
            <button
              onClick={() => setMode('approval')}
              className={`px-3 py-1.5 font-semibold transition-colors ${
                mode === 'approval'
                  ? 'bg-amber-900 text-amber-200'
                  : 'bg-slate-800 text-slate-400 hover:text-white'
              }`}
            >
              Queue for Approval
            </button>
          </div>
        </div>

        <form onSubmit={handleSend} className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          {mode === 'direct' && (
            <div className="flex items-center gap-2 bg-green-950/40 border border-green-900/50 rounded-lg px-3 py-2">
              <span className="text-green-400 text-xs">⚡</span>
              <span className="text-green-400 text-xs">Sends immediately via Meta Cloud API — no approval needed</span>
            </div>
          )}
          {mode === 'approval' && (
            <div className="flex items-center gap-2 bg-amber-950/40 border border-amber-900/50 rounded-lg px-3 py-2">
              <span className="text-amber-400 text-xs">⏱</span>
              <span className="text-amber-400 text-xs">Creates approval file in /Pending_Approval/ — move to /Approved/ to send</span>
            </div>
          )}

          <div>
            <label className="block text-slate-400 text-xs mb-1.5">
              Phone Number <span className="text-slate-600">(country code, no +, e.g. 923001234567)</span>
            </label>
            <input
              type="text"
              value={toNumber}
              onChange={e => setToNumber(e.target.value)}
              placeholder="923001234567"
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm placeholder-slate-600 focus:outline-none focus:border-cyan-600"
            />
          </div>
          <div>
            <label className="block text-slate-400 text-xs mb-1.5">Message</label>
            <textarea
              rows={4}
              value={message}
              onChange={e => setMessage(e.target.value)}
              placeholder="Type your message…"
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm placeholder-slate-600 focus:outline-none focus:border-cyan-600 resize-none"
            />
          </div>
          <div className="flex justify-end">
            <button
              type="submit"
              disabled={sending || !toNumber.trim() || !message.trim()}
              className={`text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors disabled:opacity-40 disabled:cursor-not-allowed
                ${mode === 'direct'
                  ? 'bg-green-700 hover:bg-green-600'
                  : 'bg-amber-700 hover:bg-amber-600'}`}
            >
              {sending
                ? (mode === 'direct' ? 'Sending…' : 'Queuing…')
                : (mode === 'direct' ? 'Send Now' : 'Queue for Approval')}
            </button>
          </div>
        </form>
      </section>

      {/* Message history */}
      <section>
        <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">Message History</h2>
        {loading ? (
          <div className="text-slate-500 text-sm">Loading…</div>
        ) : messages.length === 0 ? (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-10 text-center">
            <div className="text-4xl mb-2">💬</div>
            <div className="text-slate-500 text-sm">No WhatsApp messages in vault yet</div>
          </div>
        ) : (
          <div className="bg-slate-900 border border-slate-800 rounded-xl divide-y divide-slate-800/60 overflow-hidden">
            {messages.map(m => (
              <div key={m.file} className="px-4 py-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-white font-medium text-sm">{m.from || 'Unknown'}</span>
                  <div className="flex items-center gap-2">
                    {m.received && (
                      <span className="text-slate-600 text-xs font-mono">{m.received.slice(0, 16)}</span>
                    )}
                    <StatusBadge status={m.status} />
                  </div>
                </div>
                <p className="text-slate-400 text-sm">{m.message || '(no content)'}</p>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
