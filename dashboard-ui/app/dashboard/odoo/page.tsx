'use client'

import { useState, useEffect, FormEvent } from 'react'

interface OdooSummary {
  income?: number
  expenses?: number
  goal?: number
  net?: number
  invoice_count?: number
  recent_invoices?: { file: string; customer: string; amount: string }[]
}

function StatCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex-1 min-w-32">
      <div className={`text-xl font-extrabold ${color}`}>{value}</div>
      <div className="text-slate-500 text-xs uppercase tracking-wider mt-1">{label}</div>
    </div>
  )
}

export default function OdooPage() {
  const [summary, setSummary]   = useState<OdooSummary | null>(null)
  const [loading, setLoading]   = useState(true)
  const [customer, setCustomer] = useState('')
  const [amount, setAmount]     = useState('')
  const [email, setEmail]       = useState('')
  const [desc, setDesc]         = useState('')
  const [sending, setSending]   = useState(false)
  const [toast, setToast]       = useState<{ type: 'ok' | 'err'; msg: string } | null>(null)

  const showToast = (type: 'ok' | 'err', msg: string) => {
    setToast({ type, msg })
    setTimeout(() => setToast(null), 4000)
  }

  useEffect(() => {
    fetch('/api/odoo/summary')
      .then(r => r.json())
      .then(d => setSummary(d))
      .catch(() => showToast('err', 'Failed to load Odoo summary'))
      .finally(() => setLoading(false))
  }, [])

  async function handleInvoice(e: FormEvent) {
    e.preventDefault()
    if (!customer.trim() || !amount.trim()) return
    setSending(true)
    try {
      const res = await fetch('/api/odoo/invoice', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          customer: customer.trim(),
          amount: amount.trim(),
          email: email.trim(),
          description: desc.trim() || 'Professional Services',
        }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error ?? 'Unknown error')
      showToast('ok', `Invoice queued: ${data.approval_file}`)
      setCustomer('')
      setAmount('')
      setEmail('')
      setDesc('')
    } catch (err: unknown) {
      showToast('err', err instanceof Error ? err.message : 'Invoice creation failed')
    } finally {
      setSending(false)
    }
  }

  const fmt = (n?: number) => n !== undefined ? `$${n.toLocaleString()}` : '—'

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

      <h1 className="text-lg font-bold text-white">🏢 Odoo</h1>

      {/* Stats */}
      <section>
        <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">Monthly Summary</h2>
        {loading ? (
          <div className="text-slate-500 text-sm">Loading…</div>
        ) : (
          <div className="flex flex-wrap gap-3">
            <StatCard label="Income"    value={fmt(summary?.income)}   color="text-green-400" />
            <StatCard label="Expenses"  value={fmt(summary?.expenses)} color="text-red-400"   />
            <StatCard label="Net"       value={fmt(summary?.net)}      color="text-cyan-400"  />
            <StatCard label="MTD Goal"  value={fmt(summary?.goal)}     color="text-slate-300" />
            <StatCard label="Invoices"  value={String(summary?.invoice_count ?? 0)} color="text-white" />
          </div>
        )}
      </section>

      {/* Recent invoices */}
      {!loading && (summary?.recent_invoices?.length ?? 0) > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">Recent Invoices</h2>
          <div className="bg-slate-900 border border-slate-800 rounded-xl divide-y divide-slate-800/60 overflow-hidden">
            {summary!.recent_invoices!.map(inv => (
              <div key={inv.file} className="px-4 py-3 flex items-center justify-between">
                <span className="text-white text-sm">{inv.customer}</span>
                <span className="text-green-400 text-sm font-mono font-semibold">
                  {inv.amount.startsWith('$') ? inv.amount : `$${inv.amount}`}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Create invoice */}
      <section>
        <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">Create Invoice (requires approval)</h2>
        <form onSubmit={handleInvoice} className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-slate-400 text-xs mb-1.5">Customer Name *</label>
              <input
                type="text"
                value={customer}
                onChange={e => setCustomer(e.target.value)}
                placeholder="Acme Corp"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm placeholder-slate-600 focus:outline-none focus:border-cyan-600"
              />
            </div>
            <div>
              <label className="block text-slate-400 text-xs mb-1.5">Amount (USD) *</label>
              <input
                type="number"
                value={amount}
                onChange={e => setAmount(e.target.value)}
                placeholder="1500"
                min="0"
                step="0.01"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm placeholder-slate-600 focus:outline-none focus:border-cyan-600"
              />
            </div>
          </div>
          <div>
            <label className="block text-slate-400 text-xs mb-1.5">Client Email (optional)</label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="client@example.com"
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm placeholder-slate-600 focus:outline-none focus:border-cyan-600"
            />
          </div>
          <div>
            <label className="block text-slate-400 text-xs mb-1.5">Description</label>
            <input
              type="text"
              value={desc}
              onChange={e => setDesc(e.target.value)}
              placeholder="Professional Services"
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm placeholder-slate-600 focus:outline-none focus:border-cyan-600"
            />
          </div>
          <div className="flex items-center justify-between">
            <p className="text-slate-600 text-xs">Creates approval in /Pending_Approval/ — move to /Approved/ to generate PDF</p>
            <button
              type="submit"
              disabled={sending || !customer.trim() || !amount.trim()}
              className="bg-cyan-700 hover:bg-cyan-600 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors"
            >
              {sending ? 'Queuing…' : 'Create Invoice'}
            </button>
          </div>
        </form>
      </section>
    </div>
  )
}
