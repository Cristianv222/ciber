import { useEffect, useMemo, useState } from 'react'
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell,
} from 'recharts'
import api from '../api/client.js'
import { useFlowsSocket } from '../hooks/useFlowsSocket.js'
import { PageHeader, StatTile, LiveBadge } from '../components/ui.jsx'

const tooltipStyle = {
  background: 'rgb(var(--surface))', border: '1px solid rgb(var(--border))',
  borderRadius: 10, fontSize: 12, color: 'rgb(var(--fg))', boxShadow: 'var(--shadow)',
}

const SOURCE = {
  tls: { label: 'HTTPS', cls: 'bg-ok/10 text-ok border-ok/20' },
  dns: { label: 'DNS', cls: 'bg-warn/10 text-warn border-warn/20' },
  http: { label: 'HTTP', cls: 'bg-threat/10 text-threat border-threat/20' },
}

function SourceChip({ source }) {
  const s = SOURCE[source] || { label: source, cls: 'bg-surface2 text-muted border-line' }
  return <span className={`chip border ${s.cls}`}>{s.label}</span>
}

export default function Web() {
  const [summary, setSummary] = useState({ total_visits: 0, unique_domains: 0, unique_clients: 0 })
  const [top, setTop] = useState({ top_domains: [], top_clients: [], by_source: [] })
  const [recent, setRecent] = useState([])
  const [srcFilter, setSrcFilter] = useState('')  // '' = todos

  async function loadStatic() {
    const [s, t] = await Promise.all([
      api.get('/api/web-visits/summary/'),
      api.get('/api/web-visits/top/', { params: { limit: 12 } }),
    ])
    setSummary(s.data)
    setTop(t.data)
  }
  async function loadRecent() {
    const r = await api.get('/api/web-visits/', {
      params: { ordering: '-timestamp', source: srcFilter || undefined },
    })
    setRecent(r.data.results || r.data)
  }
  useEffect(() => { loadStatic().catch(() => {}) }, [])
  useEffect(() => { loadRecent().catch(() => {}) }, [srcFilter])

  const { connected } = useFlowsSocket((msg) => {
    if (msg.type === 'new_web_visit') {
      if (!srcFilter || msg.visit.source === srcFilter) {
        setRecent((p) => [msg.visit, ...p].slice(0, 100))
      }
      setSummary((s) => ({ ...s, total_visits: (s.total_visits || 0) + 1 }))
    }
  })

  const sourceCount = (src) => (top.by_source || []).find((s) => s.source === src)?.total ?? 0
  const FILTERS = [
    { key: '', label: 'Todos' },
    { key: 'tls', label: `HTTPS (${sourceCount('tls')})` },
    { key: 'dns', label: `DNS (${sourceCount('dns')})` },
    { key: 'http', label: `HTTP (${sourceCount('http')})` },
  ]

  const domainsData = useMemo(
    () => (top.top_domains || []).map((d) => ({ domain: d.domain, total: d.total })),
    [top]
  )

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <PageHeader
        title="Navegación web"
        subtitle="Sitios visitados en la red (SNI de HTTPS, consultas DNS y HTTP en claro)"
        right={<LiveBadge connected={connected} />}
      />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-5 animate-fade-up">
        <StatTile label="Visitas totales" value={(summary.total_visits ?? 0).toLocaleString()} tone="neutral" />
        <StatTile label="Dominios únicos" value={summary.unique_domains ?? 0} tone="ok" />
        <StatTile label="Clientes" value={summary.unique_clients ?? 0} tone="neutral" />
        <StatTile
          label="HTTP en claro"
          value={(top.by_source || []).find((s) => s.source === 'http')?.total ?? 0}
          tone="warn"
        />
      </div>

      <div className="grid lg:grid-cols-3 gap-4 mb-5">
        <div className="card p-5 lg:col-span-2">
          <div className="text-sm font-medium mb-4">Top sitios más visitados</div>
          <div style={{ height: Math.max(220, domainsData.length * 30) }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={domainsData} layout="vertical" margin={{ left: 20 }}>
                <XAxis type="number" stroke="rgb(var(--muted))" fontSize={11} allowDecimals={false} tickLine={false} axisLine={false} />
                <YAxis type="category" dataKey="domain" stroke="rgb(var(--muted))" fontSize={11} width={150} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={tooltipStyle} cursor={{ fill: 'rgb(var(--surface-2))' }} />
                <Bar dataKey="total" radius={[0, 5, 5, 0]} barSize={14}>
                  {domainsData.map((_, i) => <Cell key={i} fill="#9a9aa2" />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card overflow-hidden flex flex-col">
          <div className="px-5 py-3.5 border-b border-line text-sm font-medium">Clientes más activos</div>
          <div className="divide-y divide-line/60 overflow-y-auto">
            {(top.top_clients || []).map((c, i) => (
              <div key={i} className="px-5 py-2.5 flex items-center justify-between text-sm">
                <span className="font-mono text-xs text-fg-soft">{c.src_ip}</span>
                <span className="tabular-nums text-muted">{c.total}</span>
              </div>
            ))}
            {(!top.top_clients || top.top_clients.length === 0) && (
              <div className="px-5 py-8 text-center text-muted text-sm">Sin datos</div>
            )}
          </div>
        </div>
      </div>

      <div className="card overflow-hidden">
        <div className="px-5 py-3.5 border-b border-line flex items-center justify-between gap-3 flex-wrap">
          <span className="text-sm font-medium">Registro de navegación (en vivo)</span>
          <div className="flex gap-1.5">
            {FILTERS.map((f) => (
              <button
                key={f.key}
                onClick={() => setSrcFilter(f.key)}
                className={`chip border transition-colors ${
                  srcFilter === f.key
                    ? 'bg-fg text-bg border-fg'
                    : 'bg-surface2 text-muted border-line hover:text-fg'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-xs text-muted">
              <tr className="border-b border-line">
                <th className="text-left font-medium px-5 py-2.5">Hora</th>
                <th className="text-left font-medium px-5 py-2.5">Cliente</th>
                <th className="text-left font-medium px-5 py-2.5">Sitio</th>
                <th className="text-left font-medium px-5 py-2.5">Ruta</th>
                <th className="text-left font-medium px-5 py-2.5">Tipo</th>
              </tr>
            </thead>
            <tbody>
              {recent.map((v) => (
                <tr key={v.id} className="border-b border-line/60 last:border-0 hover:bg-surface2/50 transition-colors">
                  <td className="px-5 py-2.5 text-xs text-muted font-mono whitespace-nowrap">
                    {v.timestamp ? new Date(v.timestamp).toLocaleTimeString() : '—'}
                  </td>
                  <td className="px-5 py-2.5 font-mono text-xs text-fg-soft">{v.src_ip}</td>
                  <td className="px-5 py-2.5 text-fg-soft">{v.domain}</td>
                  <td className="px-5 py-2.5 font-mono text-xs text-muted max-w-xs truncate">{v.url_path || '—'}</td>
                  <td className="px-5 py-2.5"><SourceChip source={v.source} /></td>
                </tr>
              ))}
              {recent.length === 0 && (
                <tr><td colSpan={5} className="px-5 py-10 text-center text-muted">Sin navegación registrada</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
