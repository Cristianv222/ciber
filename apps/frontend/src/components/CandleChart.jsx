// Gráfica de velas (candlestick) de la evolución benigno/maligno.
// Cada vela = un tramo de flujos por orden de llegada. El "precio" es el % de
// tráfico benigno: vela verde si mejora (más benigno que el tramo anterior),
// roja si empeora (más amenazas). Wicks sintéticos para el look de trading.
export default function CandleChart({ series = [] }) {
  if (!series.length) {
    return <div className="h-56 grid place-items-center text-muted text-sm">Sin datos</div>
  }

  const W = 620, H = 220
  const padL = 34, padR = 12, padT = 14, padB = 22
  const iw = W - padL - padR
  const ih = H - padT - padB

  // OHLC a partir del % benigno
  const prices = series.map((s) => s.benign_pct)
  const candles = series.map((s, i) => {
    const open = i === 0 ? prices[0] : prices[i - 1]
    const close = prices[i]
    const base = Math.abs(close - open)
    const wick = Math.max(2.5, base * 0.6)
    return {
      ...s,
      open, close,
      high: Math.min(100, Math.max(open, close) + wick),
      low: Math.max(0, Math.min(open, close) - wick),
      up: close >= open,
    }
  })

  const lo = Math.min(...candles.map((c) => c.low))
  const hi = Math.max(...candles.map((c) => c.high))
  const span = hi - lo || 1
  const x = (i) => padL + (iw * (i + 0.5)) / series.length
  const y = (v) => padT + ((hi - v) / span) * ih
  const cw = Math.max(3, (iw / series.length) * 0.58)

  const gridVals = [lo, lo + span * 0.33, lo + span * 0.66, hi]

  return (
    <div className="relative h-56">
      {/* glow de fondo estilo terminal */}
      <div className="absolute inset-0 rounded-xl pointer-events-none"
        style={{ background: 'radial-gradient(120% 80% at 100% 50%, rgba(34,197,94,0.10), transparent 60%)' }} />
      <svg viewBox={`0 0 ${W} ${H}`} className="relative w-full h-full" preserveAspectRatio="none">
        <defs>
          <filter id="glowUp" x="-50%" y="-50%" width="200%" height="200%">
            <feDropShadow dx="0" dy="0" stdDeviation="2.2" floodColor="#22c55e" floodOpacity="0.9" />
          </filter>
          <filter id="glowDn" x="-50%" y="-50%" width="200%" height="200%">
            <feDropShadow dx="0" dy="0" stdDeviation="2.2" floodColor="#ef4444" floodOpacity="0.9" />
          </filter>
        </defs>

        {/* grid + etiquetas Y (%) */}
        {gridVals.map((v, i) => (
          <g key={i}>
            <line x1={padL} x2={W - padR} y1={y(v)} y2={y(v)} stroke="rgb(var(--border))" strokeWidth="1" opacity="0.5" />
            <text x={padL - 6} y={y(v) + 3} textAnchor="end" fontSize="9" fill="rgb(var(--muted))">{Math.round(v)}%</text>
          </g>
        ))}

        {/* velas */}
        {candles.map((c, i) => {
          const color = c.up ? '#22c55e' : '#ef4444'
          const yO = y(c.open), yC = y(c.close)
          const top = Math.min(yO, yC)
          const h = Math.max(1.5, Math.abs(yC - yO))
          return (
            <g key={i} filter={c.up ? 'url(#glowUp)' : 'url(#glowDn)'}>
              <title>{`Tramo ${c.i}: ${c.benign} benignos · ${c.threat} amenazas (${c.benign_pct}% benigno)`}</title>
              <line x1={x(i)} x2={x(i)} y1={y(c.high)} y2={y(c.low)} stroke={color} strokeWidth="1.3" />
              <rect x={x(i) - cw / 2} y={top} width={cw} height={h} rx="1" fill={color} />
            </g>
          )
        })}
      </svg>
    </div>
  )
}
