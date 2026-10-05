// Iconos de línea (SVG), 1.5px stroke — sobrios, sin emojis.
const base = {
  width: 18, height: 18, viewBox: '0 0 24 24', fill: 'none',
  stroke: 'currentColor', strokeWidth: 1.5, strokeLinecap: 'round', strokeLinejoin: 'round',
}

export const IconDashboard = (p) => (
  <svg {...base} {...p}><rect x="3" y="3" width="7" height="9" rx="1.5" /><rect x="14" y="3" width="7" height="5" rx="1.5" /><rect x="14" y="12" width="7" height="9" rx="1.5" /><rect x="3" y="16" width="7" height="5" rx="1.5" /></svg>
)

export const IconShield = (p) => (
  <svg {...base} {...p}><path d="M12 3l7 3v5c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3z" /></svg>
)

export const IconAgents = (p) => (
  <svg {...base} {...p}><rect x="4" y="8" width="16" height="12" rx="2" /><path d="M12 8V5M9 5h6M8 13h.01M16 13h.01M9 17h6" /></svg>
)

export const IconBrain = (p) => (
  <svg {...base} {...p}><path d="M9 4a3 3 0 00-3 3 3 3 0 00-1 5 3 3 0 002 5 3 3 0 004 0V4a2 2 0 00-2 0z" /><path d="M15 4a3 3 0 013 3 3 3 0 011 5 3 3 0 01-2 5 3 3 0 01-4 0" /></svg>
)

export const IconSun = (p) => (
  <svg {...base} {...p}><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></svg>
)

export const IconMoon = (p) => (
  <svg {...base} {...p}><path d="M21 12.8A9 9 0 1111.2 3a7 7 0 009.8 9.8z" /></svg>
)

export const IconLogout = (p) => (
  <svg {...base} {...p}><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9" /></svg>
)

export const IconSearch = (p) => (
  <svg {...base} {...p}><circle cx="11" cy="11" r="7" /><path d="M21 21l-4-4" /></svg>
)

export const IconArrow = (p) => (
  <svg {...base} {...p}><path d="M5 12h14M13 6l6 6-6 6" /></svg>
)

export const IconFlows = (p) => (
  <svg {...base} {...p}><path d="M3 12h4l2 6 4-14 2 8h6" /></svg>
)

export const IconHoneypot = (p) => (
  <svg {...base} {...p}><circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="4" /><circle cx="12" cy="12" r="0.5" fill="currentColor" /></svg>
)

export const IconModel = (p) => (
  <svg {...base} {...p}><path d="M12 3l8 4.5-8 4.5-8-4.5L12 3z" /><path d="M4 12l8 4.5 8-4.5M4 16.5l8 4.5 8-4.5" /></svg>
)

export const IconServer = (p) => (
  <svg {...base} {...p}><rect x="3" y="4" width="18" height="7" rx="1.5" /><rect x="3" y="13" width="18" height="7" rx="1.5" /><path d="M7 7.5h.01M7 16.5h.01" /></svg>
)

export const IconExternal = (p) => (
  <svg {...base} {...p}><path d="M14 4h6v6M20 4l-9 9M19 14v5a1 1 0 01-1 1H5a1 1 0 01-1-1V6a1 1 0 011-1h5" /></svg>
)

export const IconClose = (p) => (
  <svg {...base} {...p}><path d="M6 6l12 12M18 6L6 18" /></svg>
)
