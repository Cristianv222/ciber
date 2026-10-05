import { useEffect, useMemo, useState } from 'react'
import api from '../api/client.js'
import { useFlowsSocket } from '../hooks/useFlowsSocket.js'
import { PageHeader, LabelChip, LiveBadge } from '../components/ui.jsx'
import { IconSearch } from '../components/icons.jsx'

const BENIGN = new Set(['benign', 'BENIGN', 'unlabeled'])
const isThreat = (l) => l && !BENIGN.has(l)

export default function Attacks() {
  const [flows, setFlows] = useState([])
  const [filter, setFilter] = useState('')

  async function load() {
    const { data } = await api.get('/api/flows/', { params: { ordering: '-timestamp' } })
    setFlows(data.results || data)
  }
  useEffect(() => { load().catch(() => {}) }, [])

  const { connected } = useFlowsSocket((msg) => {
    if (msg.type === 'new_flow') setFlows((p) => [msg.flow, ...p].slice(0, 200))
    else if (msg.type === 'flow_updated') setFlows((p) => p.map((f) => (f.id === msg.flow.id ? msg.flow : f)))
  })

  const threats = useMemo(() => flows.filter((f) => isThreat(f.label)), [flows])

  const byType = useMemo(() => {
    const m = {}
    for (const f of threats) {
      const t = f.attack_type || f.label
      m[t] = (m[t] || 0) + 1
    }
    return Object.entries(m).sort((a, b) => b[1] - a[1])
  }, [threats])

  const byAttacker = useMemo(() => {
    const m = {}
    for (const f of threats) {
      const key = `${f.src_ip}||${f.attack_type || f.label}`
      if (!m[key]) m[key] = { ip: f.src_ip, type: f.attack_type || f.label, count: 0, maxCvss: 0 }
      m[key].count++
      m[key].maxCvss = Math.max(m[key].maxCvss, f.cvss_score || 0)
    }
    return Object.values(m).sort((a, b) => b.count - a.count)
  }, [threats])

  const filtered = filter
    ? byAttacker.filter((a) => a.ip.includes(filter) || a.type.toLowerCase().includes(filter.toLowerCase()))
    : byAttacker

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <PageHeader
        title="Ataques"
        subtitle="Clasificados por tipo y por IP atacante"
        right={<LiveBadge connected={connected} />}
      />

      <div className="flex flex-wrap gap-3 mb-6 animate-fade-up">
        {byType.map(([type, n]) => (
          <div key={type} className="card px-5 py-4 min-w-[140px]">
            <LabelChip label={type} />
            <div className="text-[26px] font-semibold text-threat mt-3 tabular-nums">{n}</div>
            <div className="text-xs text-muted">eventos</div>
          </div>
        ))}
        {byType.length === 0 && (
          <div className="text-muted text-sm py-4">Sin ataques detectados todavía.</div>
        )}
      </div>

      <div className="card overflow-hidden">
        <div className="px-5 py-3.5 border-b border-line flex items-center justify-between gap-3">
          <span className="text-sm font-medium">Atacantes · IP → tipo de ataque</span>
          <div className="relative">
            <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted">
              <IconSearch width={15} height={15} />
            </span>
            <input
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="Filtrar IP o tipo"
              className="field pl-8 pr-3 py-1.5 text-sm w-56"
            />
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-xs text-muted">
              <tr className="border-b border-line">
                <th className="text-left font-medium px-5 py-2.5">IP atacante</th>
                <th className="text-left font-medium px-5 py-2.5">Tipo de ataque</th>
                <th className="text-left font-medium px-5 py-2.5">Eventos</th>
                <th className="text-left font-medium px-5 py-2.5">CVSS máx.</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((a, i) => (
                <tr key={i} className="border-b border-line/60 last:border-0 hover:bg-surface2/50 transition-colors">
                  <td className="px-5 py-2.5 font-mono text-xs text-fg-soft">{a.ip}</td>
                  <td className="px-5 py-2.5"><LabelChip label={a.type} /></td>
                  <td className="px-5 py-2.5 tabular-nums">{a.count}</td>
                  <td className="px-5 py-2.5 tabular-nums">
                    <span className={a.maxCvss >= 7 ? 'text-threat' : 'text-warn'}>
                      {a.maxCvss ? a.maxCvss.toFixed(1) : '—'}
                    </span>
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr><td colSpan={4} className="px-5 py-10 text-center text-muted">Sin resultados</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
