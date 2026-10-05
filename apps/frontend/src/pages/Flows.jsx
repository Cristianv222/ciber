import { useEffect, useMemo, useState } from 'react'
import api from '../api/client.js'
import { PageHeader, LabelChip } from '../components/ui.jsx'
import { IconSearch, IconClose } from '../components/icons.jsx'

const IDENTITY = ['src_ip', 'src_port', 'dst_ip', 'dst_port', 'protocol', 'timestamp', 'label']
const PIPELINE = ['attack_type', 'confidence', 'detector_stage', 'cvss_score', 'action_taken', 'processed_at']

const humanize = (k) => k.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
const fmt = (v) => {
  if (v === null || v === undefined || v === '') return '—'
  if (typeof v === 'number' && !Number.isInteger(v)) return v.toFixed(3)
  return String(v)
}

function DetailDrawer({ flow, onClose }) {
  if (!flow) return null
  const metricKeys = Object.keys(flow).filter(
    (k) => k !== 'id' && !IDENTITY.includes(k) && !PIPELINE.includes(k)
  )
  return (
    <div className="fixed inset-0 z-40 flex justify-end">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-xl h-full bg-surface border-l border-line overflow-y-auto animate-fade-up">
        <div className="sticky top-0 bg-surface/90 backdrop-blur px-6 py-4 border-b border-line flex items-center justify-between">
          <div>
            <div className="text-sm text-muted">Flujo #{flow.id}</div>
            <div className="font-mono text-sm mt-0.5">{flow.src_ip} → {flow.dst_ip}</div>
          </div>
          <button onClick={onClose} className="btn p-2 text-muted hover:text-fg"><IconClose /></button>
        </div>

        <Section title="Identidad">
          {IDENTITY.map((k) => <Field key={k} k={k} v={k === 'label' ? null : flow[k]} chip={k === 'label' ? flow[k] : null} />)}
        </Section>
        <Section title="Clasificación del pipeline">
          {PIPELINE.map((k) => <Field key={k} k={k} v={flow[k]} />)}
        </Section>
        <Section title={`Métricas del flujo (${metricKeys.length})`}>
          {metricKeys.map((k) => <Field key={k} k={k} v={flow[k]} />)}
        </Section>
      </div>
    </div>
  )
}

function Section({ title, children }) {
  return (
    <div className="px-6 py-4 border-b border-line/60">
      <div className="text-xs uppercase tracking-wide text-muted mb-3">{title}</div>
      <div className="grid grid-cols-2 gap-x-6 gap-y-2.5">{children}</div>
    </div>
  )
}

function Field({ k, v, chip }) {
  return (
    <div className="flex items-center justify-between gap-3 text-sm">
      <span className="text-muted text-xs">{humanize(k)}</span>
      {chip ? <LabelChip label={chip} /> : <span className="font-mono text-xs text-fg-soft tabular-nums truncate">{fmt(v)}</span>}
    </div>
  )
}

export default function Flows() {
  const [rows, setRows] = useState([])
  const [count, setCount] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState(null)
  const pageSize = 50

  async function load() {
    const { data } = await api.get('/api/flows/', {
      params: { page, search: search || undefined, ordering: '-timestamp' },
    })
    setRows(data.results || data)
    setCount(data.count ?? (data.results ? data.results.length : data.length))
  }
  useEffect(() => { load().catch(() => {}) }, [page])

  function onSearch(e) {
    e.preventDefault()
    setPage(1)
    load().catch(() => {})
  }

  const pages = Math.max(1, Math.ceil(count / pageSize))

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <PageHeader
        title="Flujos de red"
        subtitle={`${count.toLocaleString()} flujos capturados · haz clic en una fila para ver las 78 métricas`}
        right={
          <form onSubmit={onSearch} className="relative">
            <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted"><IconSearch width={15} height={15} /></span>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar IP o etiqueta"
              className="field pl-8 pr-3 py-1.5 text-sm w-60"
            />
          </form>
        }
      />

      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-xs text-muted">
              <tr className="border-b border-line">
                <th className="text-left font-medium px-5 py-2.5">Hora</th>
                <th className="text-left font-medium px-5 py-2.5">Origen</th>
                <th className="text-left font-medium px-5 py-2.5">Destino</th>
                <th className="text-left font-medium px-5 py-2.5">Proto</th>
                <th className="text-left font-medium px-5 py-2.5">Clasificación</th>
                <th className="text-left font-medium px-5 py-2.5">Conf.</th>
                <th className="text-left font-medium px-5 py-2.5">CVSS</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((f) => (
                <tr
                  key={f.id}
                  onClick={() => setSelected(f)}
                  className="border-b border-line/60 last:border-0 hover:bg-surface2/60 transition-colors cursor-pointer"
                >
                  <td className="px-5 py-2.5 text-xs text-muted font-mono whitespace-nowrap">
                    {f.timestamp ? new Date(f.timestamp).toLocaleTimeString() : '—'}
                  </td>
                  <td className="px-5 py-2.5 font-mono text-xs text-fg-soft">{f.src_ip}:{f.src_port}</td>
                  <td className="px-5 py-2.5 font-mono text-xs text-fg-soft">{f.dst_ip}:{f.dst_port}</td>
                  <td className="px-5 py-2.5 text-xs tabular-nums">{f.protocol}</td>
                  <td className="px-5 py-2.5"><LabelChip label={f.label} /></td>
                  <td className="px-5 py-2.5 text-xs tabular-nums">{f.confidence != null ? `${(f.confidence * 100).toFixed(0)}%` : '—'}</td>
                  <td className="px-5 py-2.5 text-xs tabular-nums">{f.cvss_score ?? '—'}</td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr><td colSpan={7} className="px-5 py-10 text-center text-muted">Sin flujos</td></tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="flex items-center justify-between px-5 py-3 border-t border-line text-sm">
          <span className="text-muted text-xs">Página {page} de {pages}</span>
          <div className="flex gap-2">
            <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)} className="btn btn-ghost disabled:opacity-40 text-xs py-1.5">Anterior</button>
            <button disabled={page >= pages} onClick={() => setPage((p) => p + 1)} className="btn btn-ghost disabled:opacity-40 text-xs py-1.5">Siguiente</button>
          </div>
        </div>
      </div>

      <DetailDrawer flow={selected} onClose={() => setSelected(null)} />
    </div>
  )
}
