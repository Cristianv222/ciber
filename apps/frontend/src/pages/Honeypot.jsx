import { useEffect, useRef, useState } from 'react'
import api from '../api/client.js'
import { useTheme } from '../theme/ThemeContext.jsx'
import { useFlowsSocket } from '../hooks/useFlowsSocket.js'
import { StatTile, LiveBadge } from '../components/ui.jsx'
import { IconServer, IconShield, IconHoneypot, IconCompass } from '../components/icons.jsx'
import AttackGlobe from '../components/AttackGlobe.jsx'
import Modal from '../components/Modal.jsx'

const fmtTime = (t) => (t ? new Date(t).toLocaleString() : '—')
const fmtConf = (c) => (c || c === 0 ? `${(c * 100).toFixed(1)}%` : '—')
const cvssTone = (v) => (v >= 9 ? 'text-threat' : v >= 7 ? 'text-warn' : 'text-fg-soft')

// Panel flotante de cristal reutilizable
function Glass({ className = '', children }) {
  return (
    <div className={`bg-surface/80 backdrop-blur-xl border border-line rounded-xl shadow-lg ${className}`}>
      {children}
    </div>
  )
}

export default function Honeypot() {
  const [map, setMap] = useState({ points: [], countries: [], attack_types: [], total_attacks: 0, total_detected: 0, external: 0, internal: 0, target: null })
  const [summary, setSummary] = useState({ total_events: 0, top_attackers: [], services_targeted: [] })
  const [events, setEvents] = useState([])
  const [selected, setSelected] = useState(null) // punto clicado (ubicación con sus ataques)
  const [modal, setModal] = useState(null)        // 'stats' | 'countries' | 'types' | 'telemetry'
  const debounce = useRef(null)
  const { theme } = useTheme()

  async function loadMap() {
    const m = await api.get('/api/flows/attack_map/')
    setMap(m.data)
  }
  async function loadHoneypot() {
    const [s, e] = await Promise.all([
      api.get('/api/honeypot-events/summary/'),
      api.get('/api/honeypot-events/', { params: { ordering: '-timestamp' } }),
    ])
    setSummary(s.data)
    setEvents(e.data.results || e.data)
  }
  useEffect(() => { loadMap().catch(() => {}); loadHoneypot().catch(() => {}) }, [])

  const { connected } = useFlowsSocket((msg) => {
    if (msg.type === 'new_honeypot_event') {
      setEvents((p) => [msg.event, ...p].slice(0, 100))
    }
    if (msg.type === 'flow_updated' || msg.type === 'new_honeypot_event') {
      clearTimeout(debounce.current)
      debounce.current = setTimeout(() => loadMap().catch(() => {}), 2500)
    }
  })

  const topType = map.attack_types?.[0]

  return (
    <div className="relative h-screen w-full overflow-hidden bg-bg">
      {/* Fondo de estrellas (solo modo oscuro) */}
      {theme !== 'light' && <div className="absolute inset-0 starfield" />}
      {/* Globo a pantalla completa */}
      <div className="absolute inset-0">
        {map.target
          ? <AttackGlobe points={map.points} target={map.target} onSelect={setSelected} theme={theme} />
          : <div className="h-full grid place-items-center text-muted text-sm">Cargando mapa…</div>}
      </div>

      {/* Esquina superior izquierda: título + métricas en vivo */}
      <div className="absolute top-5 left-5 pointer-events-none">
        <Glass className="px-4 py-3 pointer-events-auto">
          <div className="flex items-center gap-2.5">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full rounded-full bg-threat/60 animate-breathe" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-threat" />
            </span>
            <span className="font-semibold text-sm tracking-tight">Mapa de ataques en vivo</span>
            <LiveBadge connected={connected} />
          </div>
          <div className="flex items-center gap-5 mt-2.5">
            <div>
              <div className="text-xl font-semibold tabular-nums text-threat leading-none">{map.total_attacks ?? 0}</div>
              <div className="text-[11px] text-muted mt-1">ataques · {map.external ?? 0} ext · {map.internal ?? 0} int</div>
            </div>
            <div>
              <div className="text-xl font-semibold tabular-nums leading-none">{map.countries?.length ?? 0}</div>
              <div className="text-[11px] text-muted mt-1">países</div>
            </div>
            <div>
              <div className="text-xl font-semibold tabular-nums leading-none">{map.located_points ?? map.points?.length ?? 0}</div>
              <div className="text-[11px] text-muted mt-1">orígenes</div>
            </div>
            {topType && (
              <div>
                <div className="text-sm font-medium leading-none mt-1.5">{topType.type}</div>
                <div className="text-[11px] text-muted mt-1">tipo principal</div>
              </div>
            )}
          </div>
        </Glass>
      </div>

      {/* Esquina superior derecha: barra de herramientas (abre modales) */}
      <div className="absolute top-5 right-5 pointer-events-auto">
        <Glass className="p-1.5 flex items-center gap-1">
          <ToolBtn icon={<IconServer />} label="Resumen" onClick={() => setModal('stats')} />
          <ToolBtn icon={<IconCompass />} label="Países" onClick={() => setModal('countries')} />
          <ToolBtn icon={<IconShield />} label="Tipos" onClick={() => setModal('types')} />
          <ToolBtn icon={<IconHoneypot />} label="Honeypot" onClick={() => setModal('telemetry')} />
        </Glass>
      </div>

      {/* Esquina inferior izquierda: leyenda */}
      <div className="absolute bottom-5 left-5 pointer-events-none">
        <Glass className="px-4 py-3 pointer-events-auto text-xs space-y-1.5">
          <div className="flex items-center gap-2"><span className="h-2 w-2 rounded-full bg-threat" /> Origen del ataque (país)</div>
          <div className="flex items-center gap-2"><span className="h-2 w-2 rounded-full bg-ok" /> {map.target?.label || 'Red monitoreada'}</div>
          <div className="text-muted pt-1 border-t border-line/60">Clic en un punto o arco para ver sus ataques</div>
        </Glass>
      </div>

      {/* MODAL: ataques de una ubicación (clic en el globo) */}
      <Modal
        open={!!selected}
        onClose={() => setSelected(null)}
        size="lg"
        title={selected ? `${selected.country || 'Desconocido'}${selected.city ? ' · ' + selected.city : ''}` : ''}
        subtitle={selected ? `${selected.total} ataques detectados${selected.max_cvss ? ' · CVSS máx ' + selected.max_cvss : ''}` : ''}
      >
        {selected && (
          <table className="w-full text-sm">
            <thead className="text-xs text-muted sticky top-0 bg-surface">
              <tr className="border-b border-line">
                <th className="text-left font-medium px-4 py-2.5">IP origen</th>
                <th className="text-left font-medium px-4 py-2.5">Tipo</th>
                <th className="text-left font-medium px-4 py-2.5">CVSS</th>
                <th className="text-left font-medium px-4 py-2.5">Confianza</th>
                <th className="text-left font-medium px-4 py-2.5">Etapa</th>
                <th className="text-left font-medium px-4 py-2.5">Puerto</th>
                <th className="text-left font-medium px-4 py-2.5">Hora</th>
              </tr>
            </thead>
            <tbody>
              {(selected.attacks || []).map((a) => (
                <tr key={a.id} className="border-b border-line/60 last:border-0">
                  <td className="px-4 py-2.5 font-mono text-xs text-fg-soft">{a.src_ip}</td>
                  <td className="px-4 py-2.5"><span className="chip bg-threat/10 text-threat border border-threat/20">{a.attack_type}</span></td>
                  <td className={`px-4 py-2.5 tabular-nums font-medium ${cvssTone(a.cvss_score || 0)}`}>{a.cvss_score ?? '—'}</td>
                  <td className="px-4 py-2.5 tabular-nums text-muted">{fmtConf(a.confidence)}</td>
                  <td className="px-4 py-2.5 text-xs text-muted">{a.detector_stage || '—'}</td>
                  <td className="px-4 py-2.5 tabular-nums text-muted">{a.dst_port ?? '—'}</td>
                  <td className="px-4 py-2.5 text-xs text-muted whitespace-nowrap">{fmtTime(a.timestamp)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {selected && selected.total > (selected.attacks?.length || 0) && (
          <div className="px-4 py-3 text-xs text-muted border-t border-line">
            Mostrando {selected.attacks.length} de {selected.total} ataques de esta ubicación.
          </div>
        )}
      </Modal>

      {/* MODAL: resumen / estadísticas */}
      <Modal open={modal === 'stats'} onClose={() => setModal(null)} title="Resumen de ataques" subtitle="Datos reales del pipeline de detección">
        <div className="p-5 grid grid-cols-2 gap-4">
          <StatTile label="Ataques detectados (total)" value={map.total_detected ?? 0} tone="threat" />
          <StatTile label="En el mapa" value={map.total_attacks ?? 0} tone="warn" />
          <StatTile label="Externos (país real)" value={map.external ?? 0} tone="neutral" />
          <StatTile label="Internos (red local)" value={map.internal ?? 0} tone="neutral" />
          <StatTile label="Países de origen" value={(map.countries?.length ?? 0)} tone="neutral" />
          <StatTile label="Tipos de ataque" value={map.attack_types?.length ?? 0} tone="neutral" />
        </div>
        <div className="px-5 pb-5 -mt-1">
          <p className="text-xs text-muted leading-relaxed">
            Todos los <span className="text-fg-soft">{map.total_detected ?? 0}</span> ataques del Dashboard están en el mapa,
            geolocalizados por la <span className="text-fg-soft">IP de origen real</span>:
            <span className="text-fg-soft"> {map.external ?? 0}</span> desde un país externo y
            <span className="text-fg-soft"> {map.internal ?? 0}</span> desde la <span className="text-fg-soft">red local</span>
            (IP privada 10.x / 172.16–31.x / 192.168.x → atacante dentro de la red monitoreada).
          </p>
        </div>
      </Modal>

      {/* MODAL: países */}
      <Modal open={modal === 'countries'} onClose={() => setModal(null)} title="Ataques por país" subtitle={`${map.countries?.length ?? 0} países de origen`}>
        <div className="divide-y divide-line/60">
          {(map.countries || []).map((c, i) => (
            <div key={i} className="px-5 py-2.5 flex items-center justify-between text-sm">
              <span className="text-fg-soft">{c.country}</span>
              <span className="chip bg-threat/10 text-threat border border-threat/20 tabular-nums">{c.total}</span>
            </div>
          ))}
          {(!map.countries || map.countries.length === 0) && (
            <div className="px-5 py-8 text-center text-muted text-sm">Sin ubicaciones</div>
          )}
        </div>
      </Modal>

      {/* MODAL: tipos de ataque */}
      <Modal open={modal === 'types'} onClose={() => setModal(null)} title="Tipos de ataque" subtitle="Clasificación del detector (cascada ML)">
        <div className="divide-y divide-line/60">
          {(map.attack_types || []).map((t, i) => (
            <div key={i} className="px-5 py-2.5 flex items-center justify-between text-sm">
              <span className="chip bg-threat/10 text-threat border border-threat/20">{t.type}</span>
              <span className="tabular-nums text-muted">{t.total}</span>
            </div>
          ))}
          {(!map.attack_types || map.attack_types.length === 0) && (
            <div className="px-5 py-8 text-center text-muted text-sm">Sin datos</div>
          )}
        </div>
      </Modal>

      {/* MODAL: telemetría del honeypot (atacantes, servicios, eventos) */}
      <Modal open={modal === 'telemetry'} onClose={() => setModal(null)} size="lg" title="Telemetría del honeypot" subtitle="Intentos de acceso, credenciales y comandos capturados">
        <div className="p-5 space-y-5">
          <div className="grid lg:grid-cols-2 gap-5">
            <div>
              <div className="text-xs font-medium text-muted uppercase tracking-wide mb-2">Top atacantes</div>
              <div className="card divide-y divide-line/60">
                {(summary.top_attackers || []).slice(0, 8).map((a, i) => (
                  <div key={i} className="px-4 py-2 flex items-center justify-between text-sm">
                    <span className="font-mono text-xs text-fg-soft">{a.attacker_ip}</span>
                    <span className="tabular-nums text-muted">{a.total}</span>
                  </div>
                ))}
                {(!summary.top_attackers?.length) && <div className="px-4 py-6 text-center text-muted text-sm">Sin datos</div>}
              </div>
            </div>
            <div>
              <div className="text-xs font-medium text-muted uppercase tracking-wide mb-2">Servicios atacados</div>
              <div className="card divide-y divide-line/60">
                {(summary.services_targeted || []).map((s, i) => (
                  <div key={i} className="px-4 py-2 flex items-center justify-between text-sm">
                    <span className="chip bg-surface2 border border-line text-fg-soft">{s.service}</span>
                    <span className="tabular-nums text-muted">{s.total}</span>
                  </div>
                ))}
                {(!summary.services_targeted?.length) && <div className="px-4 py-6 text-center text-muted text-sm">Sin datos</div>}
              </div>
            </div>
          </div>

          <div>
            <div className="text-xs font-medium text-muted uppercase tracking-wide mb-2">Eventos recientes</div>
            <div className="card overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-xs text-muted">
                  <tr className="border-b border-line">
                    <th className="text-left font-medium px-4 py-2">Hora</th>
                    <th className="text-left font-medium px-4 py-2">Atacante</th>
                    <th className="text-left font-medium px-4 py-2">Servicio</th>
                    <th className="text-left font-medium px-4 py-2">Usuario</th>
                    <th className="text-left font-medium px-4 py-2">Contraseña</th>
                    <th className="text-left font-medium px-4 py-2">Comando</th>
                  </tr>
                </thead>
                <tbody>
                  {events.slice(0, 40).map((e) => (
                    <tr key={e.id} className="border-b border-line/60 last:border-0">
                      <td className="px-4 py-2 text-xs text-muted font-mono whitespace-nowrap">{e.timestamp ? new Date(e.timestamp).toLocaleTimeString() : '—'}</td>
                      <td className="px-4 py-2 font-mono text-xs text-fg-soft">{e.attacker_ip}</td>
                      <td className="px-4 py-2"><span className="chip bg-surface2 border border-line text-fg-soft">{e.service}</span></td>
                      <td className="px-4 py-2 font-mono text-xs">{e.username_attempted || '—'}</td>
                      <td className="px-4 py-2 font-mono text-xs text-threat">{e.password_attempted || '—'}</td>
                      <td className="px-4 py-2 font-mono text-xs text-muted max-w-xs truncate">{e.command_executed || '—'}</td>
                    </tr>
                  ))}
                  {events.length === 0 && <tr><td colSpan={6} className="px-4 py-8 text-center text-muted">Sin eventos</td></tr>}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </Modal>
    </div>
  )
}

function ToolBtn({ icon, label, onClick }) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-muted hover:text-fg hover:bg-surface2/70 transition-colors"
    >
      <span className="shrink-0">{icon}</span>
      <span className="hidden sm:inline">{label}</span>
    </button>
  )
}
