const TYPE_COLORS: Record<string, string> = {
  email:      'bg-cyan-500',
  sla_breach: 'bg-red-500',
  invoice:    'bg-amber-500',
  whatsapp:   'bg-green-500',
  scheduled:  'bg-cyan-600',
  approval:   'bg-cyan-400',
  social:     'bg-sky-500',
  task:       'bg-slate-500',
}

export default function TypeDot({ type }: { type: string }) {
  const color = TYPE_COLORS[type] ?? 'bg-slate-500'
  return (
    <span className={`inline-block w-1.5 h-1.5 rounded-full flex-shrink-0 ${color}`} />
  )
}
