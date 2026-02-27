type Color = 'default' | 'green' | 'amber' | 'red' | 'purple' | 'cyan'

interface StatCardProps {
  icon: string
  value: number | string
  label: string
  color?: Color
  alert?: boolean
}

const VALUE_COLOR: Record<Color, string> = {
  default: 'text-white',
  green:   'text-green-400',
  amber:   'text-amber-400',
  red:     'text-red-400',
  purple:  'text-cyan-400',
  cyan:    'text-cyan-400',
}

const BORDER_COLOR: Record<Color, string> = {
  default: 'border-slate-800',
  green:   'border-green-900/40',
  amber:   'border-amber-900/40',
  red:     'border-red-900/40',
  purple:  'border-cyan-900/40',
  cyan:    'border-cyan-900/40',
}

export default function StatCard({ icon, value, label, color = 'default', alert }: StatCardProps) {
  return (
    <div
      className={`bg-slate-900 rounded-xl border p-4 transition-colors hover:border-slate-700
        ${alert ? 'border-red-900/60' : BORDER_COLOR[color]}`}
    >
      <div className="text-xl mb-2 leading-none">{icon}</div>
      <div className={`text-3xl font-extrabold leading-none mb-1.5 ${VALUE_COLOR[color]}`}>
        {value}
      </div>
      <div className="text-slate-500 text-xs uppercase tracking-widest">{label}</div>
    </div>
  )
}
