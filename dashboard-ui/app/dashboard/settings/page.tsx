'use client'

import { useState, useEffect } from 'react'

interface SettingsData {
  whatsapp: {
    cloud_configured: boolean
    webhook_port: string
    auto_reply_enabled: boolean
    daily_report_enabled: boolean
    daily_report_time: string
    daily_report_recipient: string
  }
  system: {
    dry_run: boolean
    tier: string
    agent_id: string
    dashboard_port: string
    vault_path: string
    lockdown_active: boolean
  }
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<SettingsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    fetch('/api/settings')
      .then(r => r.json())
      .then(data => {
        setSettings(data)
        setLoading(false)
      })
      .catch(() => {
        setError('Failed to load settings')
        setLoading(false)
      })
  }, [])

  if (loading) {
    return (
      <div className="p-6">
        <div className="text-center text-slate-400">Loading settings...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-950 border border-red-800 rounded-xl p-4 text-red-300">
          ❌ {error}
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 max-w-4xl space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-bold text-white">⚙️ Settings</h1>
        <span className="text-xs bg-purple-950 text-purple-400 border border-purple-800 px-2 py-0.5 rounded-full font-semibold">
          System Configuration
        </span>
      </div>

      {/* WhatsApp Settings */}
      <section className="bg-slate-900 border border-slate-800 rounded-xl p-5">
        <h2 className="text-lg font-semibold text-green-400 mb-4 flex items-center gap-2">
          <span>📱</span> WhatsApp Business API
        </h2>
        <div className="space-y-4">
          <div className="flex justify-between items-center py-2 border-b border-slate-800">
            <span className="text-slate-400">Cloud API Status</span>
            <span className={`px-3 py-1 rounded-full text-sm font-semibold ${
              settings?.whatsapp.cloud_configured 
                ? 'bg-green-950 text-green-400' 
                : 'bg-red-950 text-red-400'
            }`}>
              {settings?.whatsapp.cloud_configured ? '✅ Configured' : '❌ Not Configured'}
            </span>
          </div>
          <div className="flex justify-between items-center py-2 border-b border-slate-800">
            <span className="text-slate-400">Auto-Reply</span>
            <span className={`text-sm ${settings?.whatsapp.auto_reply_enabled ? 'text-green-400' : 'text-slate-500'}`}>
              {settings?.whatsapp.auto_reply_enabled ? '✅ Enabled' : '⬜ Disabled'}
            </span>
          </div>
          <div className="flex justify-between items-center py-2 border-b border-slate-800">
            <span className="text-slate-400">Daily Report</span>
            <span className={`text-sm ${settings?.whatsapp.daily_report_enabled ? 'text-green-400' : 'text-slate-500'}`}>
              {settings?.whatsapp.daily_report_enabled 
                ? `✅ ${settings.whatsapp.daily_report_time} UTC → ${settings.whatsapp.daily_report_recipient || 'Not set'}`
                : '⬜ Disabled'}
            </span>
          </div>
          <div className="flex justify-between items-center py-2">
            <span className="text-slate-400">Webhook Port</span>
            <span className="text-cyan-400 font-mono text-sm">{settings?.whatsapp.webhook_port}</span>
          </div>
        </div>
      </section>

      {/* System Settings */}
      <section className="bg-slate-900 border border-slate-800 rounded-xl p-5">
        <h2 className="text-lg font-semibold text-blue-400 mb-4 flex items-center gap-2">
          <span>🖥️</span> System Configuration
        </h2>
        <div className="space-y-4">
          <div className="flex justify-between items-center py-2 border-b border-slate-800">
            <span className="text-slate-400">Dry Run Mode</span>
            <span className={`px-3 py-1 rounded-full text-sm font-semibold ${
              settings?.system.dry_run 
                ? 'bg-amber-950 text-amber-400' 
                : 'bg-green-950 text-green-400'
            }`}>
              {settings?.system.dry_run ? '⚠️ Active (No real actions)' : '✅ Disabled (Live mode)'}
            </span>
          </div>
          <div className="flex justify-between items-center py-2 border-b border-slate-800">
            <span className="text-slate-400">Tier</span>
            <span className="text-purple-400 font-semibold">{settings?.system.tier}</span>
          </div>
          <div className="flex justify-between items-center py-2 border-b border-slate-800">
            <span className="text-slate-400">Agent ID</span>
            <span className="text-slate-300 font-mono text-sm">{settings?.system.agent_id}</span>
          </div>
          <div className="flex justify-between items-center py-2 border-b border-slate-800">
            <span className="text-slate-400">Dashboard Port</span>
            <span className="text-cyan-400 font-mono text-sm">{settings?.system.dashboard_port}</span>
          </div>
          <div className="flex justify-between items-center py-2 border-b border-slate-800">
            <span className="text-slate-400">Vault Path</span>
            <span className="text-slate-300 text-sm">{settings?.system.vault_path}</span>
          </div>
          <div className="flex justify-between items-center py-2">
            <span className="text-slate-400">Lockdown Mode</span>
            <span className={`px-3 py-1 rounded-full text-sm font-semibold ${
              settings?.system.lockdown_active 
                ? 'bg-red-950 text-red-400' 
                : 'bg-green-950 text-green-400'
            }`}>
              {settings?.system.lockdown_active ? '🔒 Active' : '✅ Inactive'}
            </span>
          </div>
        </div>
      </section>

      {/* Environment Variables Info */}
      <section className="bg-slate-900 border border-slate-800 rounded-xl p-5">
        <h2 className="text-lg font-semibold text-slate-400 mb-4 flex items-center gap-2">
          <span>📝</span> Configuration
        </h2>
        <div className="bg-slate-800/50 rounded-lg p-4">
          <p className="text-sm text-slate-400 mb-3">
            Settings are loaded from the <code className="bg-slate-700 px-2 py-1 rounded">.env</code> file 
            in the project root directory.
          </p>
          <p className="text-sm text-slate-500">
            To change settings, edit the .env file and restart the orchestrator:
          </p>
          <code className="block mt-2 bg-slate-950 p-3 rounded text-xs text-cyan-400 font-mono">
            cd /mnt/d/Hackathon-00/Ai-Employee<br/>
            bash start_full_automation.sh
          </code>
        </div>
      </section>

      {/* Quick Actions */}
      <section className="bg-slate-900 border border-slate-800 rounded-xl p-5">
        <h2 className="text-lg font-semibold text-slate-400 mb-4 flex items-center gap-2">
          <span>⚡</span> Quick Actions
        </h2>
        <div className="flex gap-3">
          <a
            href="/dashboard/health"
            className="flex-1 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-semibold py-3 px-6 rounded-xl transition-all text-center"
          >
            🏥 System Health
          </a>
          <a
            href="/dashboard/logs"
            className="flex-1 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold py-3 px-6 rounded-xl transition-all text-center"
          >
            📝 Activity Logs
          </a>
        </div>
      </section>
    </div>
  )
}
