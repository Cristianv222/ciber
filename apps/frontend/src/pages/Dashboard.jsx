import { useEffect, useMemo, useRef, useState } from 'react'
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell,
  AreaChart, Area, CartesianGrid,
} from 'recharts'
import api from '../api/client.js'
import { useFlowsSocket } from '../hooks/useFlowsSocket.js'
import { PageHeader, StatTile, LabelChip, LiveBadge } from '../components/ui.jsx'
import CandleChart from '../components/CandleChart.jsx'

const BENIGN = new Set(['benign', 'BENIGN', 'unlabeled'])
const isThreat = (l) => l && !BENIGN.has(l)

const tooltipStyle = {
  background: 'rgb(var(--surface))',
  border: '1px solid rgb(var(--border))',
  borderRadius: 10,
  fontSize: 12,
  color: 'rgb(var(--fg))',
  boxShadow: 'var(--shadow)',
}

export default function Dashboard() {
  const [summary, setSummary] = useState({ total_flows: 0, labels_distribution: [] })
  const [flows, setFlows] = useState([])
  const [timeline, setTimeline] = useState([])
  const [sys, setSys] = useState({ services: [] })
  const tlTimer = useRef(null)

  const loadTimeline = () =>
    api.get('/api/flows/timeline/', { params: { buckets: 30 } })
      .then((r) => setTimeline(r.data.series || []))
      .catch(() => {})

  async function loadAll() {
    const [s, f] = await Promise.all([
      api.get('/api/flows/summary/'),
      api.get('/api/flows/', { params: { ordering: '-timestamp' } }),
    ])
    setSummary(s.data)
    setFlows(f.data.results || f.data)
    loadTimeline()
  }
  useEffect(() => { loadAll().catch(() => {}) }, [])
  useEffect(() => {
    const go = () => api.get('/api/system/status/').then((r) => setSys(r.data)).catch(() => {})
    go()
    const id = setInterval(go, 6000)
    return () => clearInterval(id)
  }, [])
  // Mantiene la gráfica de flujos actualizándose aunque el WebSocket esté callado
  useEffect(() => {
    const id = setInterval(() => loadTimeline(), 10000)
    return () => clearInterval(id)
  }, [])

  // Refresco de la serie temporal al llegar flujos (con debounce)
  const bumpTimeline = () => {
    clearTimeout(tlTimer.current)
    tlTimer.current = setTimeout(() => loadTimeline(), 1500)
  }

  const { connected } = useFlowsSocket((msg) => {
    if (msg.type === 'new_flow') {
      setFlows((prev) => [msg.flow, ...prev].slice(0, 60))
      setSummary((s) => ({ ...s, total_flows: (s.total_flows || 0) + 1 }))
      bumpTimeline()
    } else if (msg.type === 'flow_updated') {
      bumpTimeline()
      setFlows((prev) => prev.map((f) => (f.id === msg.flow.id ? msg.flow : f)))
      const lbl = msg.flow?.label
      if (lbl && lbl !== 'unlabeled') {
        setSummary((s) => {
          if (!s) return s
          const curDist = (s.labels_distribution || []).map((d) => ({ ...d }))
          const idx = curDist.findIndex((d) => d.label?.toLowerCase() === lbl?.toLowerCase())
          if (idx >= 0) {
            curDist[idx] = { ...curDist[idx], total: (curDist[idx].total || 0) + 1 }
          } else {
            curDist.push({ label: lbl, total: 1 })
          }
          return { ...s, labels_distribution: curDist }
        })
      }
    }
  })

  const dist = useMemo(() => (summary.labels_distribution || []).map((d) => ({ ...d })), [summary])
  const threatCount = useMemo(
    () => dist.filter((d) => isThreat(d.label)).reduce((a, d) => a + d.total, 0),
    [dist]
  )
  const benignCount = (summary.total_flows || 0) - threatCount

  // Flujos acumulados en el tiempo (sembrado con el histórico de la BD; sube en
  // vivo y, si para el tráfico, la línea se queda donde llegó).
  const flowArea = useMemo(() => {
    let cb = 0, ct = 0
    return (timeline || []).map((s) => {
      cb += s.benign || 0
      ct += s.threat || 0
      return { i: s.i, benignos: cb, amenazas: ct, total: cb + ct }
    })
  }, [timeline])

  const topAttackers = useMemo(() => {
    const m = {}
    for (const f of flows) {
      if (!isThreat(f.label)) continue
      m[f.src_ip] = (m[f.src_ip] || 0) + 1
    }
    return Object.entries(m).sort((a, b) => b[1] - a[1]).slice(0, 6)
  }, [flows])

  const servicesUp = sys.services?.filter((s) => s.state === 'running').length || 0

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <PageHeader
        title="Dashboard"
        subtitle="Flujos de red almacenándose y clasificándose en tiempo real"
        right={<LiveBadge connected={connected} />}
      />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-5 animate-fade-up">
        <StatTile label="Flujos totales" value={summary.total_flows ?? 0} tone="neutral" />
        <StatTile label="Amenazas" value={threatCount} tone="threat" />
        <StatTile label="Benignos" value={benignCount} tone="ok" />
        <StatTile
          label="% amenazas"
          value={`${summary.total_flows ? Math.round((threatCount / summary.total_flows) * 100) : 0}%`}
          tone="warn"
        />
      </div>

      {/* Flujos acumulados en el tiempo — en vivo, sembrado con el histórico */}
      <div className="card p-5 mb-5">
        <div className="flex items-center justify-between mb-4">
          <div className="text-sm font-medium">Flujos clasificados en el tiempo</div>
          <div className="flex items-center gap-3 text-[11px] text-muted">
            <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-ok" /> benignos</span>
            <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-threat" /> amenazas</span>
          </div>
        </div>
        <div className="h-52">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={flowArea} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id="gBen" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#22c55e" stopOpacity={0.45} />
                  <stop offset="100%" stopColor="#22c55e" stopOpacity={0.02} />
                </linearGradient>
                <linearGradient id="gThr" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#ef4444" stopOpacity={0.45} />
                  <stop offset="100%" stopColor="#ef4444" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="rgb(var(--border))" vertical={false} />
              <XAxis dataKey="i" stroke="rgb(var(--muted))" fontSize={10} tickLine={false} axisLine={false} />
              <YAxis stroke="rgb(var(--muted))" fontSize={10} allowDecimals={false} tickLine={false} axisLine={false} width={34} />
              <Tooltip contentStyle={tooltipStyle} cursor={{ stroke: 'rgb(var(--border-strong))' }} />
              <Area type="monotone" dataKey="benignos" name="Benignos" stackId="1" stroke="#22c55e" fill="url(#gBen)" strokeWidth={1.75} isAnimationActive={false} />
              <Area type="monotone" dataKey="amenazas" name="Amenazas" stackId="1" stroke="#ef4444" fill="url(#gThr)" strokeWidth={1.75} isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-4 mb-5">
        <div className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="text-sm font-medium">Evolución benigno vs. amenazas</div>
            <div className="flex items-center gap-3 text-[11px] text-muted">
              <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-ok" /> más benigno</span>
              <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-threat" /> más amenazas</span>
            </div>
          </div>
          <CandleChart series={timeline} />
        </div>

        <div className="card p-5">
          <div className="text-sm font-medium mb-4">Distribución por clasificación</div>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={dist} layout="vertical" margin={{ left: 12 }}>
                <XAxis type="number" stroke="rgb(var(--muted))" fontSize={11} allowDecimals={false} tickLine={false} axisLine={false} />
                <YAxis type="category" dataKey="label" stroke="rgb(var(--muted))" fontSize={11} width={90} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={tooltipStyle} cursor={{ fill: 'rgb(var(--surface-2))' }} />
                <Bar dataKey="total" radius={[0, 5, 5, 0]} barSize={16}>
                  {dist.map((d, i) => (
                    <Cell key={i} fill={isThreat(d.label) ? '#ef4444' : '#22c55e'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-4 mb-5">
        <div className="card overflow-hidden">
          <div className="px-5 py-3.5 border-b border-line text-sm font-medium">Top atacantes (recientes)</div>
          <div className="divide-y divide-line/60">
            {topAttackers.map(([ip, n]) => (
              <div key={ip} className="px-5 py-2.5 flex items-center justify-between text-sm">
                <span className="font-mono text-xs text-fg-soft">{ip}</span>
                <span className="chip bg-threat/10 text-threat border border-threat/20 tabular-nums">{n}</span>
              </div>
            ))}
            {topAttackers.length === 0 && (
              <div className="px-5 py-8 text-center text-muted text-sm">Sin atacantes recientes</div>
            )}
          </div>
        </div>

        <div className="card overflow-hidden">
          <div className="px-5 py-3.5 border-b border-line text-sm font-medium flex items-center justify-between">
            <span>Estado del sistema</span>
            <span className="text-xs text-muted tabular-nums">{servicesUp}/{sys.services?.length || 0} activos</span>
          </div>
          <div className="grid grid-cols-2 gap-x-6 gap-y-2 p-5">
            {(sys.services || []).map((s) => {
              const ok = s.state === 'running'
              return (
                <div key={s.name} className="flex items-center gap-2 text-sm">
                  <span className={`h-2 w-2 rounded-full ${ok ? 'bg-ok' : s.state === 'absent' ? 'bg-muted' : 'bg-threat'}`} />
                  <span className="text-fg-soft text-xs truncate">{s.label}</span>
                </div>
              )
            })}
            {(!sys.services || sys.services.length === 0) && (
              <div className="col-span-2 text-center text-muted text-sm py-4">Cargando…</div>
            )}
          </div>
        </div>
      </div>

      <div className="card overflow-hidden">
        <div className="px-5 py-3.5 border-b border-line text-sm font-medium flex items-center justify-between">
          <span>Tráfico en vivo</span>
          <span className="text-xs text-muted tabular-nums">{flows.length} flujos recientes</span>
        </div>
        <div className="divide-y divide-line/50 max-h-[560px] overflow-y-auto">
          {flows.map((f) => <FlowRow key={f.id} f={f} />)}
          {flows.length === 0 && (
            <div className="px-5 py-12 text-center text-muted text-sm">Esperando flujos…</div>
          )}
        </div>
      </div>
    </div>
  )
}

// Severidad por CVSS v4.0
function cvssMeta(v) {
  if (v == null) return null
  if (v >= 9) return { label: 'Crítico', cls: 'bg-threat/15 text-threat border-threat/30' }
  if (v >= 7) return { label: 'Alto', cls: 'bg-threat/10 text-threat border-threat/25' }
  if (v >= 4) return { label: 'Medio', cls: 'bg-warn/10 text-warn border-warn/25' }
  return { label: 'Bajo', cls: 'bg-ok/10 text-ok border-ok/25' }
}

function FlowRow({ f }) {
  const threat = isThreat(f.label)
  const classified = f.label && f.label !== 'unlabeled'
  const accent = threat ? 'bg-threat' : classified ? 'bg-ok' : 'bg-muted'
  const conf = f.confidence
  const cvss = cvssMeta(f.cvss_score)

  return (
    <div className="relative pl-6 pr-5 py-3 flex items-center gap-4 hover:bg-surface2/40 transition-colors animate-fade-up">
      <span className={`absolute left-0 top-0 bottom-0 w-[3px] ${accent}`} />

      {/* origen -> destino + clasificación */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 font-mono text-xs">
          <span className="text-fg-soft truncate">{f.src_ip}<span className="text-muted">:{f.src_port}</span></span>
          <span className="text-muted shrink-0">→</span>
          <span className="text-muted truncate">{f.dst_ip}<span className="opacity-60">:{f.dst_port}</span></span>
        </div>
        <div className="mt-2 flex items-center gap-2.5">
          <LabelChip label={f.label} />
          {conf != null && (
            <div className="flex items-center gap-1.5">
              <div className="h-1.5 w-16 rounded-full bg-surface2 overflow-hidden">
                <div className={`h-full rounded-full ${threat ? 'bg-threat' : 'bg-ok'}`} style={{ width: `${Math.round(conf * 100)}%` }} />
              </div>
              <span className="text-[11px] text-muted tabular-nums">{Math.round(conf * 100)}%</span>
            </div>
          )}
        </div>
      </div>

      {/* CVSS + acción */}
      <div className="text-right shrink-0 w-28">
        {cvss ? (
          <span className={`chip border tabular-nums ${cvss.cls}`}>{f.cvss_score} · {cvss.label}</span>
        ) : (
          <span className="text-xs text-muted">sin CVSS</span>
        )}
        <div className="text-[11px] text-muted mt-1.5 truncate">{f.action_taken || (classified ? 'sin acción' : 'analizando…')}</div>
      </div>
    </div>
  )
}
