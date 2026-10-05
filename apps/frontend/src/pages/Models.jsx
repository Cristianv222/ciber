import { useEffect, useRef, useState } from 'react'
import api from '../api/client.js'
import { PageHeader, StatTile } from '../components/ui.jsx'

const MODEL_LABELS = {
  xgboost: 'XGBoost · etapa 1',
  cnn_lstm: 'CNN-LSTM · etapa 2',
  autoencoder: 'Autoencoder · etapa 3',
}

export default function Models() {
  const [info, setInfo] = useState(null)
  const [status, setStatus] = useState({ state: 'idle' })
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const poll = useRef(null)

  async function loadInfo() {
    try { setInfo((await api.get('/api/models/info/')).data) } catch (_) {}
  }
  async function loadStatus() {
    try {
      const { data } = await api.get('/api/train/status/')
      setStatus(data)
      if (data.state !== 'running' && poll.current) {
        clearInterval(poll.current); poll.current = null
        loadInfo()
      }
    } catch (_) {}
  }

  useEffect(() => {
    loadInfo(); loadStatus()
    return () => poll.current && clearInterval(poll.current)
  }, [])

  async function startTraining() {
    setErr(''); setBusy(true)
    try {
      await api.post('/api/train/')
      setStatus({ state: 'running' })
      poll.current = setInterval(loadStatus, 2500)
    } catch (e) {
      setErr(e?.response?.data?.detail || 'No se pudo iniciar el entrenamiento.')
    } finally { setBusy(false) }
  }

  const running = status.state === 'running'
  const models = info?.models || {}

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <PageHeader
        title="Modelos"
        subtitle="Cascada de detección entrenada sobre los flujos capturados"
        right={
          <button onClick={startTraining} disabled={busy || running} className="btn btn-primary disabled:opacity-50">
            {running ? 'Entrenando…' : busy ? 'Iniciando…' : 'Entrenar ahora'}
          </button>
        }
      />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-5 animate-fade-up">
        <StatTile label="Estado" value={info?.trained ? 'Entrenado' : 'Sin entrenar'} tone={info?.trained ? 'ok' : 'warn'} />
        <StatTile label="Features" value={info?.feature_columns?.length ?? '—'} tone="neutral" />
        <StatTile label="Clases" value={info?.class_names?.length ?? '—'} tone="neutral" />
        <StatTile label="Muestras" value={info?.n_samples?.toLocaleString?.() ?? '—'} tone="neutral" />
      </div>

      {err && <p className="text-xs text-threat mb-4">{err}</p>}

      <div className="grid lg:grid-cols-2 gap-4 mb-5">
        <div className="card p-5">
          <div className="text-sm font-medium mb-4">Modelos de la cascada</div>
          <div className="space-y-3">
            {['xgboost', 'cnn_lstm', 'autoencoder'].map((key) => {
              const present = info?.artifacts?.[key === 'xgboost' ? 'xgboost.pkl' : key + '.h5']
              const m = models[key]
              return (
                <div key={key} className="flex items-center justify-between border border-line rounded-lg px-4 py-3">
                  <div>
                    <div className="text-sm">{MODEL_LABELS[key]}</div>
                    <div className="text-xs text-muted mt-0.5">
                      {m?.accuracy != null && `Accuracy ${(m.accuracy * 100).toFixed(1)}%`}
                      {m?.threshold != null && `Umbral ${m.threshold.toFixed(4)}`}
                      {!m && (present ? 'Cargado' : 'No disponible')}
                    </div>
                  </div>
                  <span className={`chip border ${present ? 'bg-ok/10 text-ok border-ok/20' : 'bg-surface2 text-muted border-line'}`}>
                    {present ? 'presente' : 'ausente'}
                  </span>
                </div>
              )
            })}
          </div>
        </div>

        <div className="card p-5">
          <div className="text-sm font-medium mb-4">Clases detectables</div>
          <div className="flex flex-wrap gap-2">
            {(info?.class_names || []).map((c) => (
              <span key={c} className="chip bg-surface2 border border-line text-fg-soft">{c}</span>
            ))}
            {(!info?.class_names || info.class_names.length === 0) && (
              <span className="text-muted text-sm">Entrena los modelos para ver las clases.</span>
            )}
          </div>
          {info?.created_at && (
            <div className="text-xs text-muted mt-4">
              Último entrenamiento: {new Date(info.created_at).toLocaleString()}
            </div>
          )}
        </div>
      </div>

      {(running || status.logs) && (
        <div className="card overflow-hidden">
          <div className="px-5 py-3.5 border-b border-line text-sm font-medium flex items-center gap-2">
            {running && <span className="h-1.5 w-1.5 rounded-full bg-warn animate-breathe" />}
            Salida del entrenamiento
          </div>
          <pre className="p-5 text-xs font-mono text-fg-soft overflow-x-auto max-h-96 whitespace-pre-wrap leading-relaxed">
{status.logs || 'Iniciando…'}
          </pre>
        </div>
      )}
    </div>
  )
}
