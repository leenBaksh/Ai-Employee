'use client'

import { useEffect, useState } from 'react'
import Header from '@/components/Header'

interface AutomationStatus {
  name: string
  icon: string
  status: 'active' | 'inactive' | 'warning' | 'scheduled'
  frequency: string
  nextRun: string
  lastRun: string
  description: string
}

export default function AutomationPage() {
  const [automations, setAutomations] = useState<AutomationStatus[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Simulate fetching automation status
    const status: AutomationStatus[] = [
      {
        name: 'WhatsApp Auto-Reply',
        icon: '📱',
        status: 'active',
        frequency: 'Instant',
        nextRun: 'Always listening',
        lastRun: 'Just now',
        description: 'Auto-replies to WhatsApp messages with smart templates'
      },
      {
        name: 'Gmail Auto-Reply',
        icon: '📧',
        status: 'active',
        frequency: 'Every 30 min',
        nextRun: 'In 15 min',
        lastRun: '15 min ago',
        description: 'Smart email responses with priority detection'
      },
      {
        name: 'Gmail Advanced Features',
        icon: '✨',
        status: 'active',
        frequency: 'Every hour',
        nextRun: 'In 30 min',
        lastRun: '30 min ago',
        description: 'VIP detection, spam filtering, language support'
      },
      {
        name: 'LinkedIn Auto-Post',
        icon: '💼',
        status: 'active',
        frequency: 'Every 6 hours',
        nextRun: 'In 2 hours',
        lastRun: '4 hours ago',
        description: 'AI-generated content auto-posting'
      },
      {
        name: 'WhatsApp Daily Report',
        icon: '📊',
        status: 'active',
        frequency: 'Daily',
        nextRun: 'Today at 20:00 UTC',
        lastRun: 'Yesterday',
        description: 'Daily conversation summary via WhatsApp'
      },
      {
        name: 'Gmail Daily Digest',
        icon: '📬',
        status: 'active',
        frequency: 'Daily',
        nextRun: 'Today at 19:30 UTC',
        lastRun: 'Yesterday',
        description: 'Email activity summary'
      },
      {
        name: 'LinkedIn Daily Digest',
        icon: '📈',
        status: 'active',
        frequency: 'Daily',
        nextRun: 'Today at 19:00 UTC',
        lastRun: 'Yesterday',
        description: 'LinkedIn analytics and pipeline'
      },
      {
        name: 'SLA Monitoring',
        icon: '⏰',
        status: 'active',
        frequency: 'Every 30 min',
        nextRun: 'In 10 min',
        lastRun: '20 min ago',
        description: 'Service level agreement monitoring'
      },
      {
        name: 'Process Watchdog',
        icon: '🐕',
        status: 'active',
        frequency: 'Every 60 sec',
        nextRun: 'In 30 sec',
        lastRun: '30 sec ago',
        description: 'Auto-restart failed services'
      },
      {
        name: 'Daily Briefing',
        icon: '📋',
        status: 'active',
        frequency: 'Daily',
        nextRun: 'Tomorrow at 08:00 UTC',
        lastRun: 'Today at 08:00',
        description: 'Daily task summary and briefing'
      },
      {
        name: 'Weekly Audit',
        icon: '🔍',
        status: 'scheduled',
        frequency: 'Weekly',
        nextRun: 'Sunday at 22:00 UTC',
        lastRun: 'Last Sunday',
        description: 'Weekly comprehensive audit'
      }
    ]

    setAutomations(status)
    setLoading(false)
  }, [])

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-slate-400">Loading automation status...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <Header
        title="🤖 Automation Status"
        subtitle="All Active Automations • 24/7 Operation"
      />

      <main className="p-6 space-y-6">

        {/* Summary Cards */}
        <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-gradient-to-br from-green-950/30 to-emerald-950/30 rounded-2xl border border-green-800/30 p-6 backdrop-blur">
            <div className="text-4xl mb-3">✅</div>
            <div className="text-3xl font-bold text-green-400">11</div>
            <div className="text-sm text-green-300 mt-1">Active Automations</div>
            <div className="text-xs text-slate-400 mt-2">All systems operational</div>
          </div>

          <div className="bg-gradient-to-br from-blue-950/30 to-cyan-950/30 rounded-2xl border border-blue-800/30 p-6 backdrop-blur">
            <div className="text-4xl mb-3">⏰</div>
            <div className="text-3xl font-bold text-blue-400">24/7</div>
            <div className="text-sm text-blue-300 mt-1">Continuous Operation</div>
            <div className="text-xs text-slate-400 mt-2">No downtime</div>
          </div>

          <div className="bg-gradient-to-br from-purple-950/30 to-pink-950/30 rounded-2xl border border-purple-800/30 p-6 backdrop-blur">
            <div className="text-4xl mb-3">📊</div>
            <div className="text-3xl font-bold text-purple-400">100%</div>
            <div className="text-sm text-purple-300 mt-1">Uptime</div>
            <div className="text-xs text-slate-400 mt-2">Since deployment</div>
          </div>
        </section>

        {/* Automation List */}
        <section className="bg-slate-900/50 rounded-2xl border border-slate-800 p-6">
          <h2 className="text-lg font-bold text-slate-200 mb-4">📋 All Automations</h2>
          <div className="space-y-4">
            {automations.map((automation, index) => (
              <div
                key={index}
                className="bg-slate-800/50 rounded-xl p-4 border border-slate-700 hover:border-cyan-700 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-4 flex-1">
                    <div className="text-4xl">{automation.icon}</div>
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-1">
                        <h3 className="text-lg font-bold text-slate-200">{automation.name}</h3>
                        <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                          automation.status === 'active'
                            ? 'bg-green-950 text-green-400 border border-green-800'
                            : automation.status === 'warning'
                            ? 'bg-amber-950 text-amber-400 border border-amber-800'
                            : 'bg-slate-800 text-slate-400 border border-slate-700'
                        }`}>
                          {automation.status === 'active' ? '🟢 Active' : automation.status === 'warning' ? '🟡 Warning' : '⚪ Scheduled'}
                        </span>
                      </div>
                      <p className="text-sm text-slate-400 mb-3">{automation.description}</p>
                      
                      <div className="grid grid-cols-3 gap-4 text-xs">
                        <div>
                          <div className="text-slate-500 mb-1">Frequency</div>
                          <div className="text-slate-300 font-medium">{automation.frequency}</div>
                        </div>
                        <div>
                          <div className="text-slate-500 mb-1">Next Run</div>
                          <div className="text-cyan-400 font-medium">{automation.nextRun}</div>
                        </div>
                        <div>
                          <div className="text-slate-500 mb-1">Last Run</div>
                          <div className="text-slate-300 font-medium">{automation.lastRun}</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Quick Actions */}
        <section className="bg-gradient-to-br from-cyan-950/30 via-blue-950/30 to-purple-950/30 rounded-2xl border border-cyan-800/30 p-6 backdrop-blur">
          <h2 className="text-lg font-bold text-cyan-400 mb-4">⚡ Quick Actions</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <button className="bg-slate-800/50 hover:bg-slate-700/50 rounded-xl p-4 border border-slate-700 transition-colors text-center">
              <div className="text-2xl mb-2">🔄</div>
              <div className="text-sm font-semibold text-slate-200">Restart All</div>
            </button>
            <button className="bg-slate-800/50 hover:bg-slate-700/50 rounded-xl p-4 border border-slate-700 transition-colors text-center">
              <div className="text-2xl mb-2">📊</div>
              <div className="text-sm font-semibold text-slate-200">View Logs</div>
            </button>
            <button className="bg-slate-800/50 hover:bg-slate-700/50 rounded-xl p-4 border border-slate-700 transition-colors text-center">
              <div className="text-2xl mb-2">⚙️</div>
              <div className="text-sm font-semibold text-slate-200">Configure</div>
            </button>
            <button className="bg-slate-800/50 hover:bg-slate-700/50 rounded-xl p-4 border border-slate-700 transition-colors text-center">
              <div className="text-2xl mb-2">📈</div>
              <div className="text-sm font-semibold text-slate-200">Analytics</div>
            </button>
          </div>
        </section>

      </main>
    </div>
  )
}
