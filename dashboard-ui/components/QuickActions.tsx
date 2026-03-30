'use client'

import { useState, useEffect } from 'react'

interface QuickAction {
  label: string
  icon: string
  action: () => void
  color: string
}

export default function QuickActions() {
  const [showLockdownModal, setShowLockdownModal] = useState(false)
  const [lockdownReason, setLockdownReason] = useState('')

  const quickActions: QuickAction[] = [
    {
      label: 'Lockdown Mode',
      icon: '🔒',
      action: () => setShowLockdownModal(true),
      color: 'from-red-600 to-red-700'
    },
  ]

  const handleLockdownEnable = async () => {
    try {
      const res = await fetch('/api/lockdown/enable', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: lockdownReason || 'Manual activation' }),
      })
      if (res.ok) {
        alert('🔒 Lockdown Mode ENABLED')
        setShowLockdownModal(false)
        setLockdownReason('')
      } else {
        alert('❌ Failed to enable lockdown')
      }
    } catch {
      alert('❌ Error enabling lockdown')
    }
  }

  const handleLockdownDisable = async () => {
    try {
      const res = await fetch('/api/lockdown/disable', { method: 'POST' })
      if (res.ok) {
        alert('✅ Lockdown Mode DISABLED')
        setShowLockdownModal(false)
      } else {
        alert('❌ Failed to disable lockdown')
      }
    } catch {
      alert('❌ Error disabling lockdown')
    }
  }

  return (
    <>
      {/* Quick Actions Buttons */}
      <div className="space-y-2">
        {quickActions.map((action) => (
          <button
            key={action.label}
            onClick={action.action}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all bg-gradient-to-r ${action.color} hover:opacity-90 text-white font-medium`}
          >
            <span className="text-xl">{action.icon}</span>
            <span>{action.label}</span>
          </button>
        ))}
      </div>

      {/* Lockdown Modal */}
      {showLockdownModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 rounded-2xl border border-red-800/50 w-full max-w-md p-6">
            <div className="flex items-center gap-3 mb-6">
              <span className="text-4xl">🔒</span>
              <div>
                <h2 className="text-xl font-bold text-red-400">Lockdown Mode</h2>
                <p className="text-sm text-slate-400">Block all incoming messages</p>
              </div>
            </div>

            <div className="bg-red-950/30 border border-red-800/50 rounded-xl p-4 mb-6">
              <p className="text-sm text-red-300">
                ⚠️ When enabled, all incoming WhatsApp messages will be blocked until you disable lockdown mode.
              </p>
            </div>

            <div className="mb-6">
              <label className="block text-sm text-slate-400 mb-2">
                Reason (optional)
              </label>
              <input
                type="text"
                value={lockdownReason}
                onChange={(e) => setLockdownReason(e.target.value)}
                placeholder="Security precaution..."
                className="w-full bg-slate-800 border border-slate-700 rounded-xl p-3 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-red-500"
              />
            </div>

            <div className="flex gap-3">
              <button
                onClick={handleLockdownEnable}
                className="flex-1 bg-gradient-to-r from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 text-white font-semibold py-3 px-6 rounded-xl transition-all"
              >
                🔒 Enable Lockdown
              </button>
              <button
                onClick={handleLockdownDisable}
                className="flex-1 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold py-3 px-6 rounded-xl transition-all"
              >
                ✅ Disable
              </button>
            </div>

            <button
              onClick={() => setShowLockdownModal(false)}
              className="w-full mt-4 text-slate-400 hover:text-slate-200 py-2"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </>
  )
}

// WhatsApp Send Modal Component (unused - kept for reference)
function WhatsAppModal({ onClose, onSend }: { onClose: () => void, onSend: (to: string, msg: string) => void }) {
  const [to, setTo] = useState('')
  const [message, setMessage] = useState('')

  const handleSubmit = () => {
    if (!to.trim() || !message.trim()) {
      alert('Please fill in all fields')
      return
    }
    onSend(to, message)
  }

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur flex items-center justify-center z-50 p-4">
      <div className="bg-slate-900 rounded-2xl border border-green-800/50 w-full max-w-md p-6">
        <div className="flex items-center gap-3 mb-6">
          <span className="text-4xl">💬</span>
          <div>
            <h2 className="text-xl font-bold text-green-400">Send WhatsApp</h2>
            <p className="text-sm text-slate-400">Send message via Cloud API</p>
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm text-slate-400 mb-2">
              Phone Number
            </label>
            <input
              type="tel"
              value={to}
              onChange={(e) => setTo(e.target.value)}
              placeholder="+923103871019"
              className="w-full bg-slate-800 border border-slate-700 rounded-xl p-3 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>

          <div>
            <label className="block text-sm text-slate-400 mb-2">
              Message
            </label>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Type your message..."
              rows={4}
              className="w-full bg-slate-800 border border-slate-700 rounded-xl p-3 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-green-500 resize-none"
            />
          </div>
        </div>

        <div className="flex gap-3 mt-6">
          <button
            onClick={handleSubmit}
            className="flex-1 bg-gradient-to-r from-green-600 to-green-700 hover:from-green-500 hover:to-green-600 text-white font-semibold py-3 px-6 rounded-xl transition-all"
          >
            🚀 Send Message
          </button>
          <button
            onClick={onClose}
            className="px-6 py-3 text-slate-400 hover:text-slate-200 font-semibold"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}

// Settings Modal Component
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

function SettingsModal({ onClose }: { onClose: () => void }) {
  const [settings, setSettings] = useState<SettingsData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/settings')
      .then(r => r.json())
      .then(data => {
        setSettings(data)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  const handleQuickLink = (path: string) => {
    window.location.href = path
  }

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black/80 backdrop-blur flex items-center justify-center z-50 p-4">
        <div className="bg-slate-900 rounded-2xl border border-slate-800 w-full max-w-lg p-6">
          <div className="text-center text-slate-400">Loading settings...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur flex items-center justify-center z-50 p-4">
      <div className="bg-slate-900 rounded-2xl border border-slate-800 w-full max-w-lg p-6 max-h-[80vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <span className="text-4xl">⚙️</span>
            <div>
              <h2 className="text-xl font-bold text-slate-200">Settings</h2>
              <p className="text-sm text-slate-400">AI Employee Configuration</p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-200 text-2xl">×</button>
        </div>

        <div className="space-y-6">
          {/* WhatsApp Settings */}
          <div className="bg-slate-800/50 rounded-xl p-4">
            <h3 className="font-semibold text-green-400 mb-3">📱 WhatsApp</h3>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-400">Cloud API</span>
                <span className={settings?.whatsapp.cloud_configured ? 'text-green-400' : 'text-red-400'}>
                  {settings?.whatsapp.cloud_configured ? '✅ Configured' : '❌ Not configured'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Auto-Reply</span>
                <span className={settings?.whatsapp.auto_reply_enabled ? 'text-green-400' : 'text-slate-500'}>
                  {settings?.whatsapp.auto_reply_enabled ? '✅ Enabled' : '⬜ Disabled'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Daily Report</span>
                <span className={settings?.whatsapp.daily_report_enabled ? 'text-green-400' : 'text-slate-500'}>
                  {settings?.whatsapp.daily_report_enabled 
                    ? `✅ ${settings.whatsapp.daily_report_time} UTC → ${settings.whatsapp.daily_report_recipient || 'Not set'}`
                    : '⬜ Disabled'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Webhook Port</span>
                <span className="text-cyan-400">{settings?.whatsapp.webhook_port}</span>
              </div>
            </div>
          </div>

          {/* System Settings */}
          <div className="bg-slate-800/50 rounded-xl p-4">
            <h3 className="font-semibold text-blue-400 mb-3">🖥️ System</h3>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-400">Dry Run Mode</span>
                <span className={settings?.system.dry_run ? 'text-amber-400' : 'text-green-400'}>
                  {settings?.system.dry_run ? '⚠️ Active' : '✅ Disabled'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Tier</span>
                <span className="text-purple-400">{settings?.system.tier}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Agent ID</span>
                <span className="text-slate-300">{settings?.system.agent_id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Lockdown Mode</span>
                <span className={settings?.system.lockdown_active ? 'text-red-400' : 'text-green-400'}>
                  {settings?.system.lockdown_active ? '🔒 Active' : '✅ Inactive'}
                </span>
              </div>
            </div>
          </div>

          {/* Quick Links */}
          <div className="bg-slate-800/50 rounded-xl p-4">
            <h3 className="font-semibold text-purple-400 mb-3">🔗 Quick Links</h3>
            <div className="space-y-2">
              <button 
                onClick={() => handleQuickLink('/dashboard/tasks')}
                className="w-full text-left text-sm text-slate-400 hover:text-slate-200 py-2"
              >
                → View Activity Logs
              </button>
              <button 
                onClick={() => handleQuickLink('/dashboard/health')}
                className="w-full text-left text-sm text-slate-400 hover:text-slate-200 py-2"
              >
                → Check System Health
              </button>
              <button 
                onClick={() => handleQuickLink('/dashboard/approvals')}
                className="w-full text-left text-sm text-slate-400 hover:text-slate-200 py-2"
              >
                → Manage Approvals
              </button>
            </div>
          </div>
        </div>

        <button
          onClick={onClose}
          className="w-full mt-6 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold py-3 px-6 rounded-xl transition-all"
        >
          Close
        </button>
      </div>
    </div>
  )
}
