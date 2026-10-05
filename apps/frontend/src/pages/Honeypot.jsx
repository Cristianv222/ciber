import { useEffect, useState } from 'react'
import api from '../api/client.js'
import { useFlowsSocket } from '../hooks/useFlowsSocket.js'
import { PageHeader, StatTile, LiveBadge } from '../components/ui.jsx'
import AttackGlobe from '../components/AttackGlobe.jsx'

export default function Honeypot() {
  const [summary, setSummary] = useState({ total_events: 0, top_attackers: [], services_targeted: [] })
  const [events, setEvents] = useState([])
  const [geo, setGeo] = useState({ points: [], countries: [], target: null })

  async function load() {
    const [s, e, g] = await Promise.all([
      api.get('/api/honeypot-events/summary/'),
      api.get('/api/honeypot-events/', { params: { ordering: '-timestamp' } }),
      api.get('/api/honeypot-events/geo/'),
    ])
    setSummary(s.data)
    setEvents(e.data.results || e.data)
    setGeo(g.data)
  }
  useEffect(() => { load().catch(() => {}) }, [])

  const { connected } = useFlowsSocket((msg) => {
    if (msg.type === 'new_honeypot_event') {
      setEvents((p) => [msg.event, ...p].slice(0, 100))
      setSummary((s) => ({ ...s, total_events: (s.total_events || 0) + 1 }))
    }
  })

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <PageHeader
        title="Honeypot"
        subtitle="Telemetría de señuelos: intentos de acceso, credenciales y comandos"
        right={<LiveBadge connected={connected} />}
      />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-5 animate-fade-up">
        <StatTile label="Eventos totales" value={summary.total_events ?? 0} tone="threat" />
        <StatTile label="Atacantes únicos" value={summary.top_attackers?.length ?? 0} tone="neutral" />
        <StatTile label="Países de origen" value={geo.countries?.length ?? 0} tone="warn" />
        <StatTile label="Servicios atacados" value={summary.services_targeted?.length ?? 0} tone="neutral" />
      </div>

      {/* Mapa mundial de ataques (globo 3D) */}
      <div className="grid lg:grid-cols-3 gap-4 mb-5">
        <div className="card p-2 lg:col-span-2 overflow-hidden">
          <div className="px-3 py-2.5 text-sm font-medium flex items-center justify-between">
            <span>Origen de los ataques</span>
            <span className="text-xs text-muted">arrastra para rotar · rueda para acercar</span>
          </div>
          {geo.target && <AttackGlobe points={geo.points} target={geo.target} />}
        </div>
        <div className="card overflow-hidden flex flex-col">
          <div className="px-5 py-3.5 border-b border-line text-sm font-medium">Ataques por país</div>
          <div className="divide-y divide-line/60 overflow-y-auto">
            {(geo.countries || []).map((c, i) => (
              <div key={i} className="px-5 py-2.5 flex items-center justify-between text-sm">
                <span className="text-fg-soft">{c.country}</span>
                <span className="chip bg-threat/10 text-threat border border-threat/20 tabular-nums">{c.total}</span>
              </div>
            ))}
            {(!geo.countries || geo.countries.length === 0) && (
              <div className="px-5 py-8 text-center text-muted text-sm">Sin ubicaciones (IPs reservadas o sin datos)</div>
            )}
          </div>
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-4 mb-5">
        <div className="card overflow-hidden">
          <div className="px-5 py-3.5 border-b border-line text-sm font-medium">Top atacantes</div>
          <div className="divide-y divide-line/60">
            {(summary.top_attackers || []).map((a, i) => (
              <div key={i} className="px-5 py-2.5 flex items-center justify-between text-sm">
                <span className="font-mono text-xs text-fg-soft">{a.attacker_ip}</span>
                <span className="tabular-nums text-muted">{a.total}</span>
              </div>
            ))}
            {(!summary.top_attackers || summary.top_attackers.length === 0) && (
              <div className="px-5 py-8 text-center text-muted text-sm">Sin datos</div>
            )}
          </div>
        </div>

        <div className="card overflow-hidden">
          <div className="px-5 py-3.5 border-b border-line text-sm font-medium">Servicios atacados</div>
          <div className="divide-y divide-line/60">
            {(summary.services_targeted || []).map((s, i) => (
              <div key={i} className="px-5 py-2.5 flex items-center justify-between text-sm">
                <span className="chip bg-surface2 border border-line text-fg-soft">{s.service}</span>
                <span className="tabular-nums text-muted">{s.total}</span>
              </div>
            ))}
            {(!summary.services_targeted || summary.services_targeted.length === 0) && (
              <div className="px-5 py-8 text-center text-muted text-sm">Sin datos</div>
            )}
          </div>
        </div>
      </div>

      <div className="card overflow-hidden">
        <div className="px-5 py-3.5 border-b border-line text-sm font-medium">Eventos recientes</div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-xs text-muted">
              <tr className="border-b border-line">
                <th className="text-left font-medium px-5 py-2.5">Hora</th>
                <th className="text-left font-medium px-5 py-2.5">Atacante</th>
                <th className="text-left font-medium px-5 py-2.5">Servicio</th>
                <th className="text-left font-medium px-5 py-2.5">Usuario</th>
                <th className="text-left font-medium px-5 py-2.5">Contraseña</th>
                <th className="text-left font-medium px-5 py-2.5">Comando</th>
              </tr>
            </thead>
            <tbody>
              {events.map((e) => (
                <tr key={e.id} className="border-b border-line/60 last:border-0 hover:bg-surface2/50 transition-colors">
                  <td className="px-5 py-2.5 text-xs text-muted font-mono whitespace-nowrap">
                    {e.timestamp ? new Date(e.timestamp).toLocaleTimeString() : '—'}
                  </td>
                  <td className="px-5 py-2.5 font-mono text-xs text-fg-soft">{e.attacker_ip}</td>
                  <td className="px-5 py-2.5"><span className="chip bg-surface2 border border-line text-fg-soft">{e.service}</span></td>
                  <td className="px-5 py-2.5 font-mono text-xs">{e.username_attempted || '—'}</td>
                  <td className="px-5 py-2.5 font-mono text-xs text-threat">{e.password_attempted || '—'}</td>
                  <td className="px-5 py-2.5 font-mono text-xs text-muted max-w-xs truncate">{e.command_executed || '—'}</td>
                </tr>
              ))}
              {events.length === 0 && (
                <tr><td colSpan={6} className="px-5 py-10 text-center text-muted">Sin eventos de honeypot</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
