import { useEffect, useRef, useState } from 'react'
import { useFlowsSocket } from '../hooks/useFlowsSocket.js'
import { PageHeader, LiveBadge } from '../components/ui.jsx'
import { IconShield, IconAgents, IconBrain, IconArrow, IconExternal } from '../components/icons.jsx'

const STAGES = [
  { key: 'detector', title: 'Detector', Icon: IconAgents, desc: 'Cascada ML clasifica el flujo', url: 'http://localhost:10000/spade' },
  { key: 'decision', title: 'Decisión', Icon: IconBrain, desc: 'Calcula CVSS v4.0', url: 'http://localhost:10001/spade' },
  { key: 'response', title: 'Respuesta', Icon: IconShield, desc: 'Bloquea con iptables', url: 'http://localhost:10002/spade' },
]

export default function Agents() {
  const [events, setEvents] = useState([])
  const [active, setActive] = useState(null)
  const timer = useRef(null)

  const { connected } = useFlowsSocket((msg) => {
    if (msg.type !== 'flow_updated') return
    const f = msg.flow
    let stage = 'detector'
    if (f.action_taken) stage = 'response'
    else if (f.cvss_score != null) stage = 'decision'
    setActive(stage)
    clearTimeout(timer.current)
    timer.current = setTimeout(() => setActive(null), 1100)
    setEvents((p) => [{
      id: f.id, ts: new Date().toLocaleTimeString(),
      label: f.label, attack: f.attack_type, cvss: f.cvss_score, action: f.action_taken, stage,
    }, ...p].slice(0, 40))
  })

  useEffect(() => () => clearTimeout(timer.current), [])

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <PageHeader
        title="Agentes"
        subtitle="Cómo recibe, detecta y actúa el sistema autónomo, en tiempo real"
        right={<LiveBadge connected={connected} />}
      />

      <div className="flex items-stretch justify-center gap-3 md:gap-5 mb-8 flex-wrap animate-fade-up">
        {STAGES.map((s, i) => {
          const on = active === s.key
          return (
            <div key={s.key} className="flex items-center gap-3 md:gap-5">
              <div
                className="card p-5 w-48 text-center transition-all duration-200 ease-out"
                style={on ? { borderColor: 'rgb(var(--fg))', transform: 'translateY(-2px)' } : undefined}
              >
                <div className={`mx-auto mb-3 inline-flex h-10 w-10 items-center justify-center rounded-xl border transition-colors ${
                  on ? 'border-fg text-fg' : 'border-line text-muted'
                }`}>
                  <s.Icon width={20} height={20} />
                </div>
                <div className="font-medium text-[15px]">{s.title}</div>
                <div className="text-xs text-muted mt-1">{s.desc}</div>
                <a
                  href={s.url}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-3 inline-flex items-center gap-1.5 text-xs text-muted hover:text-fg transition-colors"
                >
                  Abrir panel <IconExternal width={13} height={13} />
                </a>
              </div>
              {i < STAGES.length - 1 && (
                <span className={`transition-colors duration-200 ${on ? 'text-fg' : 'text-line-strong'}`}>
                  <IconArrow width={22} height={22} />
                </span>
              )}
            </div>
          )
        })}
      </div>

      <div className="card overflow-hidden">
        <div className="px-5 py-3.5 border-b border-line text-sm font-medium">Bitácora en vivo</div>
        <div className="max-h-[440px] overflow-y-auto divide-y divide-line/60">
          {events.map((e, i) => (
            <div key={i} className="px-5 py-3 text-sm flex items-center gap-3 flex-wrap">
              <span className="text-xs text-muted font-mono w-20 shrink-0">{e.ts}</span>
              <span className="chip bg-surface2 border border-line text-fg-soft capitalize">{e.stage}</span>
              <span className="text-fg-soft">flujo #{e.id}</span>
              {e.attack && <span className="chip bg-threat/10 text-threat border border-threat/20">{e.attack}</span>}
              {e.cvss != null && <span className="text-warn text-xs tabular-nums">CVSS {e.cvss}</span>}
              {e.action && <span className="text-xs text-muted">· {e.action}</span>}
            </div>
          ))}
          {events.length === 0 && (
            <div className="px-5 py-12 text-center text-muted text-sm">
              Esperando actividad del pipeline…
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
