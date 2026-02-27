import type { Metadata } from 'next'
import './globals.css'
import { DashboardProvider } from '@/context/DashboardContext'
import { ToastProvider } from '@/components/Toast'
import Header from '@/components/Header'
import Sidebar from '@/components/Sidebar'

export const metadata: Metadata = {
  title: 'AI Employee — Live Dashboard',
  description: 'Platinum Tier — AI Employee Vault Live Dashboard',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body suppressHydrationWarning>
        {/* DashboardProvider holds the single SSE connection — persists across page navigations */}
        <DashboardProvider>
          <ToastProvider>
            <div className="flex h-screen flex-col bg-slate-950 text-white overflow-hidden">
              <Header />
              <div className="flex flex-1 overflow-hidden">
                <Sidebar />
                <main className="flex-1 overflow-auto">
                  {children}
                </main>
              </div>
            </div>
          </ToastProvider>
        </DashboardProvider>
      </body>
    </html>
  )
}
