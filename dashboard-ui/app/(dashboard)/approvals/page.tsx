'use client'

import { useState } from 'react'
import { useDashboardContext, TaskItem } from '@/context/DashboardContext'
import TypeDot from '@/components/TypeDot'
import { useToast } from '@/components/Toast'

// ── Helpers ───────────────────────────────────────────────────────────────────

function ageClass(s: number) {
  if (s > 86400) return 'text-red-400'
  if (s > 3600)  return 'text-amber-400'
  return 'text-slate-400'
}

const TYPE_BADGE: Record<string, string> = {
  email:    'bg-cyan-950   text-cyan-400   border-cyan-900',
  whatsapp: 'bg-green-950  text-green-400  border-green-900',
  invoice:  'bg-amber-950  text-amber-400  border-amber-900',
  social:   'bg-sky-950    text-sky-400    border-sky-900',
  approval: 'bg-cyan-950   text-cyan-400   border-cyan-900',
  task:     'bg-slate-800  text-slate-400  border-slate-700',
}

// ── Approval Card ─────────────────────────────────────────────────────────────

function ApprovalCard({
  item,
  onDone,
}: {
  item: TaskItem
  onDone: (filename: string) => void
}) {
  const [approving, setApproving] = useState(false)
  const [rejecting, setRejecting] = useState(false)
  const [fading,    setFading]    = useState(false)
  const { showToast } = useToast()

  const busy = approving || rejecting

  async function act(action: 'approve' | 'reject') {
    if (busy) return
    action === 'approve' ? setApproving(true) : setRejecting(true)

    try {
      const res = await fetch(`/api/${action}/${encodeURIComponent(item.filename)}`, {
        method: 'POST',
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)

      const emoji = action === 'approve' ? '✅' : '❌'
      const word  = action === 'approve' ? 'Approved' : 'Rejected'
      showToast(`${emoji} ${word}: ${item.filename}`, action === 'approve' ? 'success' : 'error')

      setFading(true)
      setTimeout(() => onDone(item.filename), 350)
    } catch {
      showToast('⚠️ Action failed — is the Flask server running?', 'error')
      setApproving(false)
      setRejecting(false)
    }
  }

  const badge = TYPE_BADGE[item.type] ?? TYPE_BADGE.task

  return (
    <div
      className={`bg-slate-900 border border-slate-800 rounded-xl p-4
        flex items-center justify-between gap-4 transition-all duration-300
        ${fading ? 'opacity-0 scale-95 pointer-events-none' : 'opacity-100 scale-100'}`}
    >
      {/* Left: info */}
      <div className="flex items-center gap-3 min-w-0 flex-1">
        <TypeDot type={item.type} />
        <span className="font-mono text-cyan-400 text-sm truncate" title={item.filename}>
          {item.filename}
        </span>
        <span className={`text-xs px-2 py-0.5 rounded-full border flex-shrink-0 ${badge}`}>
          {item.type}
        </span>
        <span className={`text-xs flex-shrink-0 ${ageClass(item.age_seconds)}`}>
          {item.age_human}
        </span>
      </div>

      {/* Right: action buttons */}
      <div className="flex items-center gap-2 flex-shrink-0">
        <button
          onClick={() => act('approve')}
          disabled={busy}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold
            bg-green-900/50 border border-green-700 text-green-300
            hover:bg-green-800/60 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {approving && (
            <span className="w-3 h-3 border border-green-400 border-t-transparent rounded-full animate-spin" />
          )}
          Approve
        </button>

        <button
          onClick={() => act('reject')}
          disabled={busy}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold
            bg-red-900/50 border border-red-700 text-red-300
            hover:bg-red-800/60 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {rejecting && (
            <span className="w-3 h-3 border border-red-400 border-t-transparent rounded-full animate-spin" />
          )}
          Reject
        </button>
      </div>
    </div>
  )
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function ApprovalsPage() {
  const { data } = useDashboardContext()
  const [dismissed, setDismissed] = useState<Set<string>>(new Set())

  // SSE refreshes data; dismissed tracks locally-actioned items until SSE catches up
  const items = (data?.approvals ?? []).filter(a => !dismissed.has(a.filename))

  function dismiss(filename: string) {
    setDismissed(prev => new Set([...prev, filename]))
  }

  return (
    <div className="p-6">

      <div className="flex items-center gap-3 mb-5">
        <h1 className="text-lg font-bold text-white">Pending Approvals</h1>
        {items.length > 0 && (
          <span className="bg-cyan-900/40 text-cyan-300 text-xs font-bold px-2 py-0.5
            rounded-full border border-cyan-800">
            {items.length}
          </span>
        )}
      </div>

      {items.length === 0 ? (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-16 text-center">
          <div className="text-5xl mb-4">✅</div>
          <div className="text-slate-200 text-lg font-medium">No items pending approval</div>
          <div className="text-slate-500 text-sm mt-1">All clear — nothing waiting for review</div>
        </div>
      ) : (
        <div className="space-y-3">
          {items.map(item => (
            <ApprovalCard key={item.filename} item={item} onDone={dismiss} />
          ))}
        </div>
      )}
    </div>
  )
}
