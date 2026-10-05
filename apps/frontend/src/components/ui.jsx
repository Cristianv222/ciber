// Componentes de presentación — paleta casi monocroma, color solo en estados.

export function PageHeader({ title, subtitle, right }) {
  return (
    <div className="flex items-end justify-between gap-4 mb-7 animate-fade-up">
      <div>
        <h1 className="text-[22px] font-semibold tracking-tightest leading-none">{title}</h1>
        {subtitle && <p className="text-sm text-muted mt-2">{subtitle}</p>}
      </div>
      {right}
    </div>
  )
}

export function StatTile({ label, value, tone = 'neutral', hint }) {
  const toneMap = {
    neutral: 'text-fg',
    threat: 'text-threat',
    warn: 'text-warn',
    ok: 'text-ok',
  }
  return (
    <div className="card p-5">
      <div className="text-xs text-muted uppercase tracking-wide">{label}</div>
      <div className={`text-[28px] font-semibold mt-2 tracking-tight tabular-nums ${toneMap[tone]}`}>
        {value}
      </div>
      {hint && <div className="text-xs text-muted mt-1">{hint}</div>}
    </div>
  )
}

const BENIGN = new Set(['benign', 'BENIGN', 'unlabeled'])

export function LabelChip({ label }) {
  if (!label) return <span className="text-muted">—</span>
  let cls = 'bg-threat/10 text-threat border border-threat/20'
  if (label === 'unlabeled') cls = 'bg-surface2 text-muted border border-line'
  else if (BENIGN.has(label)) cls = 'bg-ok/10 text-ok border border-ok/20'
  else if (label === 'anomaly') cls = 'bg-warn/10 text-warn border border-warn/20'
  return <span className={`chip ${cls}`}>{label}</span>
}

export function LiveBadge({ connected }) {
  return (
    <span
      className={`chip border ${
        connected ? 'bg-ok/10 text-ok border-ok/20' : 'bg-threat/10 text-threat border-threat/20'
      }`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${connected ? 'bg-ok animate-breathe' : 'bg-threat'}`} />
      {connected ? 'En vivo' : 'Reconectando'}
    </span>
  )
}
