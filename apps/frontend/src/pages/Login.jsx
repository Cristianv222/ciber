import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import anime from 'animejs/lib/anime.es.js'
import ThreeBackground from '../components/ThreeBackground.jsx'
import { useAuth } from '../auth/AuthContext.jsx'

export default function Login() {
  const { login, user } = useAuth()
  const navigate = useNavigate()
  const cardRef = useRef(null)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (user) navigate('/')
  }, [user, navigate])

  useEffect(() => {
    anime({
      targets: cardRef.current,
      opacity: [0, 1],
      translateY: [12, 0],
      scale: [0.98, 1],
      easing: 'cubicBezier(0.23, 1, 0.32, 1)',
      duration: 600,
    })
  }, [])

  async function onSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(username, password)
      navigate('/')
    } catch (err) {
      setError(
        err?.response?.status === 401
          ? 'Usuario o contraseña incorrectos.'
          : 'No se pudo conectar con el servidor.'
      )
      anime({ targets: cardRef.current, translateX: [-6, 6, -4, 4, 0], duration: 320, easing: 'easeOutQuad' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="relative min-h-screen flex items-center justify-center overflow-hidden bg-bg">
      <ThreeBackground />
      <div
        className="absolute inset-0 -z-10"
        style={{ background: 'radial-gradient(60% 50% at 50% 42%, transparent, rgb(var(--bg)) 85%)' }}
      />

      <div ref={cardRef} className="card w-full max-w-sm p-8">
        <div className="flex items-center gap-2.5 mb-1">
          <span className="h-2 w-2 rounded-full bg-ok animate-breathe" />
          <span className="font-semibold tracking-tightest text-[15px]">
            CIBER<span className="text-muted font-normal"> / NIDS</span>
          </span>
        </div>
        <p className="text-sm text-muted mb-7">Sistema autónomo de monitoreo y respuesta</p>

        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label className="text-xs text-muted">Usuario</label>
            <input
              className="field mt-1.5 w-full px-3 py-2 text-sm"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoFocus
              autoComplete="username"
            />
          </div>
          <div>
            <label className="text-xs text-muted">Contraseña</label>
            <input
              type="password"
              className="field mt-1.5 w-full px-3 py-2 text-sm"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </div>

          {error && <p className="text-xs text-threat">{error}</p>}

          <button type="submit" disabled={loading} className="btn btn-primary w-full disabled:opacity-50">
            {loading ? 'Verificando…' : 'Ingresar'}
          </button>
        </form>

        <p className="text-[11px] text-muted mt-7 text-center">Credenciales del panel Django</p>
      </div>
    </div>
  )
}
