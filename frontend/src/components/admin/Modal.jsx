import { useEffect } from 'react'
import { X } from 'lucide-react'

export default function Modal({ title, onClose, children }) {
  useEffect(() => {
    const onKey = e => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return <div className="fixed inset-0 z-50 grid place-items-center bg-black/50 p-4" onClick={onClose}>
    <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl bg-kSurface p-6" onClick={e => e.stopPropagation()}>
      <div className="mb-5 flex items-center justify-between">
        <h3 className="font-display text-xl font-bold text-kGreen">{title}</h3>
        <button onClick={onClose} className="grid h-8 w-8 place-items-center rounded-full text-kMuted hover:bg-kBorderSoft"><X size={18} /></button>
      </div>
      {children}
    </div>
  </div>
}
