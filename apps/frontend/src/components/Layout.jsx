import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'
import { useTheme } from '../theme/ThemeContext.jsx'
import {
  IconDashboard, IconShield, IconAgents, IconModel, IconLogout, IconSun, IconMoon,
  IconFlows, IconHoneypot, IconServer,
} from './icons.jsx'

const nav = [
  { to: '/', label: 'Dashboard', Icon: IconDashboard, end: true },
  { to: '/flujos', label: 'Flujos', Icon: IconFlows },
  { to: '/ataques', label: 'Ataques', Icon: IconShield },
  { to: '/honeypot', label: 'Honeypot', Icon: IconHoneypot },
  { to: '/agentes', label: 'Agentes', Icon: IconAgents },
  { to: '/modelos', label: 'Modelos', Icon: IconModel },
  { to: '/sistema', label: 'Sistema', Icon: IconServer },
]

export default function Layout() {
  const { user, logout } = useAuth()
  const { theme, toggle } = useTheme()
  const navigate = useNavigate()

  function doLogout() {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen flex bg-bg">
      <aside className="w-60 shrink-0 border-r border-line bg-surface/70 backdrop-blur-xl flex flex-col sticky top-0 h-screen">
        <div className="px-5 py-5">
          <div className="flex items-center gap-2.5">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full rounded-full bg-ok/60 animate-breathe" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-ok" />
            </span>
            <span className="font-semibold tracking-tightest text-[15px]">
              CIBER<span className="text-muted font-normal"> / NIDS</span>
            </span>
          </div>
          <p className="text-xs text-muted mt-1 ml-[18px]">Monitoreo autónomo de red</p>
        </div>

        <nav className="flex-1 px-3 space-y-0.5">
          {nav.map(({ to, label, Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `group flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors duration-150 ${
                  isActive
                    ? 'bg-surface2 text-fg'
                    : 'text-muted hover:text-fg hover:bg-surface2/60'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <span className={isActive ? 'text-fg' : 'text-muted group-hover:text-fg'}>
                    <Icon />
                  </span>
                  {label}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="p-3 border-t border-line space-y-1">
          <button
            onClick={toggle}
            className="btn btn-ghost w-full justify-start text-muted"
            aria-label="Cambiar tema"
          >
            {theme === 'dark' ? <IconSun /> : <IconMoon />}
            <span>{theme === 'dark' ? 'Tema claro' : 'Tema oscuro'}</span>
          </button>

          <div className="flex items-center justify-between gap-2 px-3 pt-2">
            <div className="min-w-0">
              <div className="text-[11px] text-muted uppercase tracking-wide">Sesión</div>
              <div className="text-sm truncate">{user?.username}</div>
            </div>
            <button
              onClick={doLogout}
              className="btn p-2 text-muted hover:text-threat"
              aria-label="Cerrar sesión"
              title="Cerrar sesión"
            >
              <IconLogout />
            </button>
          </div>
        </div>
      </aside>

      <main className="flex-1 min-w-0 overflow-x-hidden">
        <Outlet />
      </main>
    </div>
  )
}
