import { DashboardProvider } from '@/context/DashboardContext'
import { ToastProvider } from '@/components/Toast'
import Header from '@/components/Header'
import Sidebar from '@/components/Sidebar'

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
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
  )
}
