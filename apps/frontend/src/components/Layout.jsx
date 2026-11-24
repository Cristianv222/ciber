import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'
import { useTheme } from '../theme/ThemeContext.jsx'
import {
  IconDashboard, IconShield, IconAgents, IconModel, IconLogout, IconSun, IconMoon,
  IconFlows, IconHoneypot, IconServer, IconCompass,
} from './icons.jsx'

const nav = [
  { to: '/', label: 'Dashboard', Icon: IconDashboard, end: true },
  { to: '/flujos', label: 'Flujos', Icon: IconFlows },
  { to: '/navegacion', label: 'Navegación', Icon: IconCompass },
  { to: '/ataques', label: 'Ataques', Icon: IconShield },
  { to: '/honeypot', label: 'Honeypot', Icon: IconHoneypot },
  { to: '/agentes', label: 'Agentes', Icon: IconAgents },
  { to: '/modelos', label: 'Modelos', Icon: IconModel },
  { to: '/sistema', label: 'Sistema', Icon: IconServer },
]

const IconChevron = ({ open }) => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
    strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"
    style={{ transform: open ? 'none' : 'rotate(180deg)', transition: 'transform 200ms' }}>
    <path d="M15 18l-6-6 6-6" />
  </svg>
)

export default function Layout() {
  const { user, logout } = useAuth()
  const { theme, toggle } = useTheme()
  const navigate = useNavigate()
  const [collapsed, setCollapsed] = useState(() => {
    try { return localStorage.getItem('ares_sidebar_collapsed') === '1' } catch { return false }
  })

  function toggleCollapsed() {
    setCollapsed((c) => {
      const n = !c
      try { localStorage.setItem('ares_sidebar_collapsed', n ? '1' : '0') } catch (_) {}
      return n
    })
  }

  function doLogout() {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen flex bg-bg">
      <aside
        className={`${collapsed ? 'w-[76px]' : 'w-60'} shrink-0 bg-rail text-rail-fg border-r border-rail-line
          flex flex-col sticky top-0 h-screen transition-[width] duration-200 ease-out`}
      >
        {/* Logo ARES (variante según el tema para que se vea sobre la barra) */}
        <div className={`flex items-center ${collapsed ? 'justify-center px-2' : 'px-5'} py-5 h-[92px]`}>
          {collapsed ? (
            <img src={theme === 'light' ? '/ares-mark-dark.png' : '/ares-mark.png'} alt="ARES" className="h-9 w-auto" />
          ) : (
            <img src={theme === 'light' ? '/ares-full-dark.png' : '/ares-full.png'} alt="ARES" className="h-[72px] w-auto mx-auto" />
          )}
        </div>

        <nav className="flex-1 px-3 space-y-0.5 overflow-y-auto">
          {nav.map(({ to, label, Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              title={collapsed ? label : undefined}
              className={({ isActive }) =>
                `group relative flex items-center ${collapsed ? 'justify-center' : ''} gap-3 px-3 py-2 rounded-lg text-sm transition-colors duration-150 ${
                  isActive
                    ? 'bg-rail-active text-accent'
                    : 'text-rail-muted hover:text-rail-fg hover:bg-rail-surface'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <span className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-[3px] rounded-r bg-accent" />
                  )}
                  <span className={isActive ? 'text-accent' : 'text-rail-muted group-hover:text-rail-fg'}>
                    <Icon />
                  </span>
                  {!collapsed && label}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="p-3 border-t border-rail-line space-y-1">
          <button
            onClick={toggle}
            className={`w-full flex items-center ${collapsed ? 'justify-center' : 'justify-start'} gap-3 px-3 py-2 rounded-lg text-sm text-rail-muted hover:text-rail-fg hover:bg-rail-surface transition-colors`}
            title={theme === 'dark' ? 'Tema claro' : 'Tema oscuro'}
          >
            {theme === 'dark' ? <IconSun /> : <IconMoon />}
            {!collapsed && <span>{theme === 'dark' ? 'Tema claro' : 'Tema oscuro'}</span>}
          </button>

          <button
            onClick={toggleCollapsed}
            className={`w-full flex items-center ${collapsed ? 'justify-center' : 'justify-start'} gap-3 px-3 py-2 rounded-lg text-sm text-rail-muted hover:text-rail-fg hover:bg-rail-surface transition-colors`}
            title={collapsed ? 'Expandir' : 'Colapsar'}
          >
            <IconChevron open={!collapsed} />
            {!collapsed && <span>Colapsar</span>}
          </button>

          <div className={`flex items-center ${collapsed ? 'justify-center' : 'justify-between'} gap-2 px-3 pt-2`}>
            {!collapsed && (
              <div className="min-w-0">
                <div className="text-[11px] text-rail-muted uppercase tracking-wide">Sesión</div>
                <div className="text-sm truncate text-rail-fg">{user?.username}</div>
              </div>
            )}
            <button
              onClick={doLogout}
              className="p-2 rounded-lg text-rail-muted hover:text-threat hover:bg-rail-surface transition-colors"
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
