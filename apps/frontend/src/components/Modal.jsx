import { useEffect } from 'react'
import { IconClose } from './icons.jsx'

// Modal sobrio: backdrop con blur, panel centrado, Escape para cerrar.
// Respeta prefers-reduced-motion (sin animación de entrada si el usuario lo pide).
export default function Modal({ open, onClose, title, subtitle, children, size = 'md' }) {
  useEffect(() => {
    if (!open) return
    const onKey = (e) => { if (e.key === 'Escape') onClose?.() }
    window.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [open, onClose])

  if (!open) return null

  const maxW = size === 'lg' ? 'max-w-3xl' : size === 'sm' ? 'max-w-sm' : 'max-w-xl'

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6"
      role="dialog"
      aria-modal="true"
      aria-label={title}
    >
      <div
        className="absolute inset-0 bg-bg/70 backdrop-blur-sm animate-fade"
        onClick={onClose}
      />
      <div
        className={`relative w-full ${maxW} max-h-[85vh] flex flex-col card shadow-2xl animate-fade-up`}
      >
        <div className="flex items-start justify-between gap-4 px-5 py-4 border-b border-line">
          <div className="min-w-0">
            <h2 className="text-[15px] font-semibold tracking-tight truncate">{title}</h2>
            {subtitle && <p className="text-xs text-muted mt-0.5">{subtitle}</p>}
          </div>
          <button
            onClick={onClose}
            className="btn p-1.5 -mr-1 text-muted hover:text-fg shrink-0"
            aria-label="Cerrar"
          >
            <IconClose />
          </button>
        </div>
        <div className="overflow-y-auto">{children}</div>
      </div>
    </div>
  )
}
