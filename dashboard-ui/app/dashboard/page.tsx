'use client'

import { useDashboardContext } from '@/context/DashboardContext'

export default function DashboardPage() {
  const { data, connected } = useDashboardContext()

  if (!data) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-slate-400 text-lg">Loading dashboard...</p>
        </div>
      </div>
    )
  }

  const { stats } = data

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      {/* Fixed Top Navbar */}
      <nav className="fixed top-0 left-0 right-0 h-16 bg-slate-900/95 backdrop-blur border-b border-slate-800 z-50 shadow-lg">
        <div className="px-6 h-full flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-xl font-bold text-white">
              AI
            </div>
            <div>
              <h1 className="text-lg font-bold bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
                AI Employee
              </h1>
              <p className="text-xs text-slate-400">
                {connected ? '🟢 Live' : '🟡 Connecting...'}
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-6">
            {/* Current Time */}
            <div className="hidden md:block text-right">
              <div className="text-sm font-mono text-cyan-400">
                {new Date().toLocaleTimeString()}
              </div>
              <div className="text-xs text-slate-500">
                {new Date().toLocaleDateString()}
              </div>
            </div>
            
            {/* Status Indicator */}
            <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-800/50 rounded-full border border-slate-700">
              <div className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500 animate-pulse' : 'bg-amber-500'}`} />
              <span className="text-xs text-slate-300">{connected ? 'Online' : 'Offline'}</span>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content - with padding for fixed navbar */}
      <main className="pt-20 pb-6 px-6 space-y-6">
        
        {/* Stats Grid */}
        <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Needs Action */}
          <div className="bg-slate-900/50 backdrop-blur rounded-2xl p-6 border border-amber-800/30 hover:border-amber-700/50 transition-all group">
            <div className="flex items-center justify-between mb-4">
              <span className="text-4xl">⚠️</span>
              <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                stats.needs_action > 10 
                  ? 'bg-red-950 text-red-400 border border-red-800' 
                  : 'bg-amber-950 text-amber-400 border border-amber-800'
              }`}>
                {stats.needs_action > 10 ? 'High' : 'Normal'}
              </span>
            </div>
            <div className="text-4xl font-bold text-amber-400 mb-2">{stats.needs_action}</div>
            <div className="text-sm text-slate-400">Needs Action</div>
            <div className="text-xs text-slate-500 mt-2">Requires attention</div>
          </div>

          {/* Pending Approval */}
          <div className="bg-slate-900/50 backdrop-blur rounded-2xl p-6 border border-purple-800/30 hover:border-purple-700/50 transition-all group">
            <div className="flex items-center justify-between mb-4">
              <span className="text-4xl">🔐</span>
              <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                stats.pending_approval > 0 
                  ? 'bg-purple-950 text-purple-400 border border-purple-800' 
                  : 'bg-green-950 text-green-400 border border-green-800'
              }`}>
                {stats.pending_approval > 0 ? 'Pending' : 'Clear'}
              </span>
            </div>
            <div className="text-4xl font-bold text-purple-400 mb-2">{stats.pending_approval}</div>
            <div className="text-sm text-slate-400">Pending Approval</div>
            <div className="text-xs text-slate-500 mt-2">Awaiting review</div>
          </div>

          {/* Completed */}
          <div className="bg-slate-900/50 backdrop-blur rounded-2xl p-6 border border-green-800/30 hover:border-green-700/50 transition-all group">
            <div className="flex items-center justify-between mb-4">
              <span className="text-4xl">✅</span>
              <span className="px-3 py-1 rounded-full text-xs font-semibold bg-green-950 text-green-400 border border-green-800">
                All Time
              </span>
            </div>
            <div className="text-4xl font-bold text-green-400 mb-2">{stats.done}</div>
            <div className="text-sm text-slate-400">Completed Tasks</div>
            <div className="text-xs text-slate-500 mt-2">Great progress!</div>
          </div>

          {/* SLA Breaches */}
          <div className="bg-slate-900/50 backdrop-blur rounded-2xl p-6 border border-red-800/30 hover:border-red-700/50 transition-all group">
            <div className="flex items-center justify-between mb-4">
              <span className="text-4xl">🚨</span>
              <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                stats.sla_breaches > 0 
                  ? 'bg-red-950 text-red-400 border border-red-800' 
                  : 'bg-green-950 text-green-400 border border-green-800'
              }`}>
                {stats.sla_breaches > 0 ? 'Critical' : 'OK'}
              </span>
            </div>
            <div className="text-4xl font-bold text-red-400 mb-2">{stats.sla_breaches}</div>
            <div className="text-sm text-slate-400">SLA Breaches</div>
            <div className="text-xs text-slate-500 mt-2">
              {stats.sla_breaches > 0 ? 'Needs review' : 'All within SLA'}
            </div>
          </div>
        </section>

        {/* Service Status */}
        <section className="bg-gradient-to-br from-cyan-950/30 via-blue-950/30 to-purple-950/30 rounded-2xl border border-cyan-800/30 p-6 backdrop-blur">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-xl font-bold text-cyan-400">🏥 Service Health</h2>
              <p className="text-sm text-slate-400 mt-1">Real-time monitoring</p>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              <span className="text-sm text-green-400 font-semibold">All Systems Operational</span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700 hover:border-cyan-700 transition-colors">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-2xl">📱</span>
                <span className="text-sm font-semibold">WhatsApp</span>
              </div>
              <div className="text-green-400 text-sm font-semibold">● Online</div>
              <div className="text-xs text-slate-400 mt-1">Auto-reply active</div>
            </div>
            <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700 hover:border-cyan-700 transition-colors">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-2xl">📧</span>
                <span className="text-sm font-semibold">Gmail</span>
              </div>
              <div className="text-green-400 text-sm font-semibold">● Online</div>
              <div className="text-xs text-slate-400 mt-1">Auto-reply enabled</div>
            </div>
            <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700 hover:border-cyan-700 transition-colors">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-2xl">💼</span>
                <span className="text-sm font-semibold">LinkedIn</span>
              </div>
              <div className="text-green-400 text-sm font-semibold">● Online</div>
              <div className="text-xs text-slate-400 mt-1">Auto-posting ready</div>
            </div>
            <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700 hover:border-cyan-700 transition-colors">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-2xl">⏰</span>
                <span className="text-sm font-semibold">Scheduler</span>
              </div>
              <div className="text-green-400 text-sm font-semibold">● Online</div>
              <div className="text-xs text-slate-400 mt-1">All jobs active</div>
            </div>
          </div>
        </section>

        {/* Automation Status */}
        <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* WhatsApp Gold Tier */}
          <section className="bg-gradient-to-br from-cyan-950/30 via-blue-950/30 to-purple-950/30 rounded-2xl border border-cyan-800/30 p-6 backdrop-blur">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-xl font-bold text-cyan-400">📱 WhatsApp Gold Tier</h2>
                <p className="text-sm text-slate-400 mt-1">Platinum Feature • Fully Automated</p>
              </div>
              <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            </div>

            <div className="grid grid-cols-2 gap-4 mb-6">
              <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
                <div className="text-3xl font-bold text-cyan-400">{stats.needs_action}</div>
                <div className="text-xs text-slate-400 mt-2">💬 Messages</div>
              </div>
              <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
                <div className="text-3xl font-bold text-purple-400">14</div>
                <div className="text-xs text-slate-400 mt-2">🎯 Types</div>
              </div>
            </div>

            <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
              <h3 className="text-sm font-semibold text-slate-300 mb-3">📊 Conversation Types</h3>
              <div className="flex flex-wrap gap-2">
                <span className="px-3 py-1 bg-green-950/50 border border-green-800 rounded-full text-xs text-green-400">👋 Greetings</span>
                <span className="px-3 py-1 bg-blue-950/50 border border-blue-800 rounded-full text-xs text-blue-400">💬 Questions</span>
                <span className="px-3 py-1 bg-purple-950/50 border border-purple-800 rounded-full text-xs text-purple-400">📢 Requests</span>
                <span className="px-3 py-1 bg-amber-950/50 border border-amber-800 rounded-full text-xs text-amber-400">🙏 Thanks</span>
              </div>
            </div>
          </section>

          {/* Gmail Automation */}
          <section className="bg-gradient-to-br from-red-950/30 via-orange-950/30 to-yellow-950/30 rounded-2xl border border-red-800/30 p-6 backdrop-blur">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-xl font-bold text-red-400">📧 Gmail Automation</h2>
                <p className="text-sm text-slate-400 mt-1">Smart Auto-Reply • 5 Languages</p>
              </div>
              <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
                <div className="text-2xl font-bold text-red-400">✅</div>
                <div className="text-xs text-slate-400 mt-2">Auto-Reply</div>
              </div>
              <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
                <div className="text-2xl font-bold text-blue-400">5</div>
                <div className="text-xs text-slate-400 mt-2">Languages</div>
              </div>
              <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
                <div className="text-2xl font-bold text-green-400">30m</div>
                <div className="text-xs text-slate-400 mt-2">Check</div>
              </div>
            </div>
          </section>
        </section>

      </main>
    </div>
  )
}
