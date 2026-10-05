import { useEffect, useMemo, useState } from 'react'
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell,
  AreaChart, Area, CartesianGrid,
} from 'recharts'
import api from '../api/client.js'
import { useFlowsSocket } from '../hooks/useFlowsSocket.js'
import { PageHeader, StatTile, LabelChip, LiveBadge } from '../components/ui.jsx'

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
  const [rate, setRate] = useState([])
  const [incoming, setIncoming] = useState(0)
  const [sys, setSys] = useState({ services: [] })

  async function loadAll() {
    const [s, f] = await Promise.all([
      api.get('/api/flows/summary/'),
      api.get('/api/flows/', { params: { ordering: '-timestamp' } }),
    ])
    setSummary(s.data)
    setFlows(f.data.results || f.data)
  }
  useEffect(() => { loadAll().catch(() => {}) }, [])
  useEffect(() => {
    const go = () => api.get('/api/system/status/').then((r) => setSys(r.data)).catch(() => {})
    go()
    const id = setInterval(go, 6000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    const id = setInterval(() => {
      setRate((prev) => [...prev, { t: new Date().toLocaleTimeString().slice(3), n: incoming }].slice(-30))
      setIncoming(0)
    }, 2000)
    return () => clearInterval(id)
  }, [incoming])

  const { connected } = useFlowsSocket((msg) => {
    if (msg.type === 'new_flow') {
      setIncoming((n) => n + 1)
      setFlows((prev) => [msg.flow, ...prev].slice(0, 60))
      setSummary((s) => ({ ...s, total_flows: (s.total_flows || 0) + 1 }))
    } else if (msg.type === 'flow_updated') {
      setFlows((prev) => prev.map((f) => (f.id === msg.flow.id ? msg.flow : f)))
    }
  })

  const dist = useMemo(() => (summary.labels_distribution || []).map((d) => ({ ...d })), [summary])
  const threatCount = useMemo(
    () => dist.filter((d) => isThreat(d.label)).reduce((a, d) => a + d.total, 0),
    [dist]
  )
  const benignCount = (summary.total_flows || 0) - threatCount

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

      <div className="grid lg:grid-cols-2 gap-4 mb-5">
        <div className="card p-5">
          <div className="text-sm font-medium mb-4">Ingesta en vivo · flujos / 2s</div>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={rate}>
                <defs>
                  <linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#8b8b94" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#8b8b94" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="rgb(var(--border))" vertical={false} />
                <XAxis dataKey="t" stroke="rgb(var(--muted))" fontSize={11} tickLine={false} axisLine={false} />
                <YAxis stroke="rgb(var(--muted))" fontSize={11} allowDecimals={false} tickLine={false} axisLine={false} width={24} />
                <Tooltip contentStyle={tooltipStyle} cursor={{ stroke: 'rgb(var(--border-strong))' }} />
                <Area type="monotone" dataKey="n" stroke="#9a9aa2" fill="url(#g)" strokeWidth={1.75} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
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
        <div className="px-5 py-3.5 border-b border-line text-sm font-medium">Últimos flujos</div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-xs text-muted">
              <tr className="border-b border-line">
                <th className="text-left font-medium px-5 py-2.5">Origen</th>
                <th className="text-left font-medium px-5 py-2.5">Destino</th>
                <th className="text-left font-medium px-5 py-2.5">Clasificación</th>
                <th className="text-left font-medium px-5 py-2.5">Confianza</th>
                <th className="text-left font-medium px-5 py-2.5">CVSS</th>
                <th className="text-left font-medium px-5 py-2.5">Acción</th>
              </tr>
            </thead>
            <tbody>
              {flows.map((f) => (
                <tr key={f.id} className="border-b border-line/60 last:border-0 hover:bg-surface2/50 transition-colors">
                  <td className="px-5 py-2.5 font-mono text-xs text-fg-soft">{f.src_ip}:{f.src_port}</td>
                  <td className="px-5 py-2.5 font-mono text-xs text-fg-soft">{f.dst_ip}:{f.dst_port}</td>
                  <td className="px-5 py-2.5"><LabelChip label={f.label} /></td>
                  <td className="px-5 py-2.5 text-xs tabular-nums">{f.confidence != null ? `${(f.confidence * 100).toFixed(0)}%` : '—'}</td>
                  <td className="px-5 py-2.5 text-xs tabular-nums">{f.cvss_score ?? '—'}</td>
                  <td className="px-5 py-2.5 text-xs text-muted">{f.action_taken ?? '—'}</td>
                </tr>
              ))}
              {flows.length === 0 && (
                <tr><td colSpan={6} className="px-5 py-10 text-center text-muted">Sin flujos todavía</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
