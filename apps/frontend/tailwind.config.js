/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // Tokens de tema (conmutables vía variables CSS; canales RGB para opacidad)
        bg: 'rgb(var(--bg) / <alpha-value>)',
        surface: 'rgb(var(--surface) / <alpha-value>)',
        surface2: 'rgb(var(--surface-2) / <alpha-value>)',
        line: 'rgb(var(--border) / <alpha-value>)',
        'line-strong': 'rgb(var(--border-strong) / <alpha-value>)',
        fg: 'rgb(var(--fg) / <alpha-value>)',
        'fg-soft': 'rgb(var(--fg-soft) / <alpha-value>)',
        muted: 'rgb(var(--muted) / <alpha-value>)',
        // Marca (teal del logo ARES)
        accent: 'rgb(var(--accent) / <alpha-value>)',
        brand: 'rgb(var(--brand) / <alpha-value>)',
        // Barra lateral oscura (constante en ambos temas)
        rail: 'rgb(var(--rail-bg) / <alpha-value>)',
        'rail-surface': 'rgb(var(--rail-surface) / <alpha-value>)',
        'rail-line': 'rgb(var(--rail-border) / <alpha-value>)',
        'rail-fg': 'rgb(var(--rail-fg) / <alpha-value>)',
        'rail-fg-soft': 'rgb(var(--rail-fg-soft) / <alpha-value>)',
        'rail-muted': 'rgb(var(--rail-muted) / <alpha-value>)',
        'rail-active': 'rgb(var(--rail-active) / <alpha-value>)',
        // Estados
        threat: '#ef4444',
        warn: '#f59e0b',
        ok: '#22c55e',
      },
      fontFamily: {
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      letterSpacing: {
        tightest: '-0.03em',
      },
      transitionTimingFunction: {
        out: 'cubic-bezier(0.23, 1, 0.32, 1)',
        'in-out': 'cubic-bezier(0.77, 0, 0.175, 1)',
      },
      keyframes: {
        'fade-up': {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        breathe: {
          '0%,100%': { opacity: '0.35' },
          '50%': { opacity: '1' },
        },
        fade: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
      animation: {
        'fade-up': 'fade-up 400ms cubic-bezier(0.23, 1, 0.32, 1) both',
        breathe: 'breathe 2.4s ease-in-out infinite',
        fade: 'fade 200ms ease-out both',
      },
    },
  },
  plugins: [],
}
