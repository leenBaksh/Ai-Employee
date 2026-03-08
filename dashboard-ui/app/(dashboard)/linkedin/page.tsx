'use client'

import { useState, useEffect, FormEvent } from 'react'

interface LinkedInPost {
  file: string
  status: string
  preview: string
  folder: string
}

function StatusBadge({ status }: { status: string }) {
  const cfg: Record<string, string> = {
    'pending_approval': 'bg-amber-950 text-amber-400',
    'queued':           'bg-blue-950 text-blue-400',
    'posted':           'bg-green-950 text-green-400',
    'Done':             'bg-slate-800 text-slate-400',
  }
  const cls = cfg[status] ?? 'bg-slate-800 text-slate-400'
  return <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${cls}`}>{status}</span>
}

export default function LinkedInPage() {
  const [posts, setPosts]       = useState<LinkedInPost[]>([])
  const [loading, setLoading]   = useState(true)
  const [content, setContent]   = useState('')
  const [sending, setSending]   = useState(false)
  const [toast, setToast]       = useState<{ type: 'ok' | 'err'; msg: string } | null>(null)
  const charLimit = 3000
  const remaining = charLimit - content.length

  const showToast = (type: 'ok' | 'err', msg: string) => {
    setToast({ type, msg })
    setTimeout(() => setToast(null), 4000)
  }

  useEffect(() => {
    fetch('/api/linkedin/posts')
      .then(r => r.json())
      .then(d => setPosts(d.posts ?? []))
      .catch(() => showToast('err', 'Failed to load posts'))
      .finally(() => setLoading(false))
  }, [])

  async function handleDraft(e: FormEvent) {
    e.preventDefault()
    if (!content.trim()) return
    setSending(true)
    try {
      const res = await fetch('/api/linkedin/draft', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: content.trim() }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error ?? 'Unknown error')
      showToast('ok', `Post queued for approval: ${data.approval_file}`)
      setContent('')
      // Refresh posts list
      fetch('/api/linkedin/posts').then(r => r.json()).then(d => setPosts(d.posts ?? []))
    } catch (err: unknown) {
      showToast('err', err instanceof Error ? err.message : 'Draft failed')
    } finally {
      setSending(false)
    }
  }

  const tips = [
    'Share a business win or insight to build authority',
    'Ask a question to drive engagement',
    'Tell a short story about a customer problem you solved',
    'Share industry news with your take',
  ]

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

      <h1 className="text-lg font-bold text-white">💼 LinkedIn</h1>

      {/* Post composer */}
      <section>
        <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">Write a Post (requires approval)</h2>
        <form onSubmit={handleDraft} className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <div>
            <textarea
              rows={7}
              value={content}
              onChange={e => setContent(e.target.value.slice(0, charLimit))}
              placeholder="Share an insight, business update, or success story…"
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm placeholder-slate-600 focus:outline-none focus:border-cyan-600 resize-none"
            />
            <div className={`text-xs mt-1 text-right ${remaining < 100 ? 'text-red-400' : 'text-slate-600'}`}>
              {remaining} chars remaining
            </div>
          </div>

          {/* Quick tips */}
          <div className="bg-slate-800/50 rounded-lg p-3 space-y-1">
            <p className="text-slate-500 text-xs font-semibold uppercase tracking-wider mb-2">Post ideas</p>
            {tips.map((tip, i) => (
              <button
                key={i}
                type="button"
                onClick={() => setContent(prev => prev ? prev + '\n\n' + tip : tip)}
                className="block w-full text-left text-slate-400 hover:text-cyan-300 text-xs py-0.5 transition-colors"
              >
                + {tip}
              </button>
            ))}
          </div>

          <div className="flex items-center justify-between">
            <p className="text-slate-600 text-xs">Queued to /To_Post/LinkedIn/ — needs approval to publish</p>
            <button
              type="submit"
              disabled={sending || !content.trim()}
              className="bg-cyan-700 hover:bg-cyan-600 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors"
            >
              {sending ? 'Queuing…' : 'Queue Post'}
            </button>
          </div>
        </form>
      </section>

      {/* Post list */}
      <section>
        <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">Recent & Pending Posts</h2>
        {loading ? (
          <div className="text-slate-500 text-sm">Loading…</div>
        ) : posts.length === 0 ? (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-10 text-center">
            <div className="text-4xl mb-2">💼</div>
            <div className="text-slate-500 text-sm">No LinkedIn posts found in vault</div>
          </div>
        ) : (
          <div className="bg-slate-900 border border-slate-800 rounded-xl divide-y divide-slate-800/60 overflow-hidden">
            {posts.map(p => (
              <div key={p.file} className="px-4 py-3">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-slate-500 text-xs font-mono truncate max-w-xs">{p.file}</span>
                  <StatusBadge status={p.status} />
                </div>
                <p className="text-slate-300 text-sm leading-snug line-clamp-2">{p.preview || '(no content)'}</p>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
