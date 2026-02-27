'use client'

import { useDashboardContext } from '@/context/DashboardContext'

export default function Header() {
  const { connected, data } = useDashboardContext()

  return (
    <header className="bg-slate-900 border-b border-slate-800 px-6 py-3.5 flex items-center justify-between flex-shrink-0 z-10">
      <div className="flex items-center gap-3">
        <span className="text-white font-bold text-lg">&#129302; AI Employee Dashboard</span>
        <span className="bg-cyan-950/50 text-cyan-400 border border-cyan-800/50 px-2.5 py-0.5 rounded-full text-xs font-bold tracking-widest uppercase">
          Platinum
        </span>
      </div>

      <div className="flex items-center gap-4">
        {data?.generated_at && (
          <span className="text-slate-500 text-xs hidden sm:block">
            {new Date(data.generated_at).toLocaleTimeString()}
          </span>
        )}
        <div className="flex items-center gap-2 text-xs tracking-wider">
          <span
            className={`w-2 h-2 rounded-full ${
              connected
                ? 'bg-cyan-400 animate-pulse'
                : 'bg-red-500'
            }`}
          />
          <span className={connected ? 'text-cyan-400' : 'text-slate-500'}>
            {connected ? 'LIVE' : 'POLLING'}
          </span>
        </div>
      </div>
    </header>
  )
}
