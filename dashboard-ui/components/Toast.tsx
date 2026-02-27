'use client'

import { createContext, useContext, useState, useCallback, ReactNode } from 'react'

// ── Types ─────────────────────────────────────────────────────────────────────

interface Toast {
  id: number
  message: string
  type: 'success' | 'error' | 'info'
}

interface ToastContextType {
  showToast: (message: string, type?: Toast['type']) => void
}

// ── Context ───────────────────────────────────────────────────────────────────

const ToastContext = createContext<ToastContextType>({ showToast: () => {} })

let _id = 0

// ── Provider ──────────────────────────────────────────────────────────────────

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const showToast = useCallback((message: string, type: Toast['type'] = 'info') => {
    const id = ++_id
    setToasts(prev => [...prev, { id, message, type }])
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id))
    }, 3000)
  }, [])

  const toastStyles: Record<Toast['type'], string> = {
    success: 'bg-green-950 border-green-800 text-green-200',
    error:   'bg-red-950 border-red-800 text-red-200',
    info:    'bg-slate-800 border-slate-600 text-slate-200',
  }

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      {/* Fixed toast container — bottom-right */}
      <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 pointer-events-none">
        {toasts.map(toast => (
          <div
            key={toast.id}
            className={`px-4 py-3 rounded-xl text-sm font-medium shadow-2xl border animate-fade-in pointer-events-auto
              ${toastStyles[toast.type]}`}
          >
            {toast.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useToast() {
  return useContext(ToastContext)
}
