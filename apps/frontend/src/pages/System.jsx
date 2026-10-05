import { useEffect, useState } from 'react'
import api from '../api/client.js'
import { PageHeader } from '../components/ui.jsx'
import { IconExternal } from '../components/icons.jsx'

const LINKS = [
  { label: 'Grafana', href: 'http://localhost:3000', desc: 'Dashboards de métricas' },
  { label: 'Django Admin', href: 'http://localhost:8000/admin/', desc: 'Gestión de datos' },
  { label: 'API REST', href: 'http://localhost:8000/api/flows/', desc: 'Endpoints navegables' },
  { label: 'Agente Detector', href: 'http://localhost:10000/spade', desc: 'Dashboard SPADE' },
  { label: 'Agente Decisión', href: 'http://localhost:10001/spade', desc: 'Dashboard SPADE' },
  { label: 'Agente Respuesta', href: 'http://localhost:10002/spade', desc: 'Dashboard SPADE' },
]

function stateColor(s) {
  if (s.state === 'running' && (s.health === 'healthy' || s.health === null)) return 'ok'
  if (s.state === 'running') return 'warn'
  return 'threat'
}

export default function System() {
  const [status, setStatus] = useState({ services: [] })

  async function load() {
    try { setStatus((await api.get('/api/system/status/')).data) } catch (_) {}
  }
  useEffect(() => {
    load()
    const id = setInterval(load, 5000)
    return () => clearInterval(id)
  }, [])

  const up = status.services?.filter((s) => s.state === 'running').length || 0
  const total = status.services?.length || 0

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <PageHeader
        title="Sistema"
        subtitle={`Estado de los contenedores · ${up}/${total} activos`}
      />

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-7 animate-fade-up">
        {status.services?.map((s) => {
          const tone = stateColor(s)
          const dot = { ok: 'bg-ok', warn: 'bg-warn', threat: 'bg-threat' }[tone]
          return (
            <div key={s.name} className="card p-4 flex items-center justify-between">
              <div>
                <div className="text-sm font-medium">{s.label}</div>
                <div className="text-xs text-muted font-mono mt-0.5">{s.name}</div>
              </div>
              <div className="flex items-center gap-2">
                <span className={`h-2 w-2 rounded-full ${dot} ${tone === 'ok' ? 'animate-breathe' : ''}`} />
                <span className="text-xs text-muted">
                  {s.state === 'absent' ? 'detenido' : s.health || s.state}
                </span>
              </div>
            </div>
          )
        })}
        {total === 0 && <div className="text-muted text-sm">Cargando estado…</div>}
      </div>

      <div className="text-xs uppercase tracking-wide text-muted mb-3">Accesos directos</div>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {LINKS.map((l) => (
          <a
            key={l.label}
            href={l.href}
            target="_blank"
            rel="noreferrer"
            className="card p-4 flex items-center justify-between hover:border-line-strong transition-colors group"
          >
            <div>
              <div className="text-sm font-medium">{l.label}</div>
              <div className="text-xs text-muted mt-0.5">{l.desc}</div>
            </div>
            <span className="text-muted group-hover:text-fg transition-colors"><IconExternal /></span>
          </a>
        ))}
      </div>
    </div>
  )
}
