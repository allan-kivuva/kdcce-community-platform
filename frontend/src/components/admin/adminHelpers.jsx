import { useState } from 'react'
import { AlertCircle } from 'lucide-react'
import { ApiError } from '../../lib/api'

export function useToast() {
  const [toast, setToast] = useState('')
  function show(message) { setToast(message); window.clearTimeout(show._t); show._t = window.setTimeout(() => setToast(''), 2200) }
  return [toast, show]
}

export function errorMessage(err) {
  return err instanceof ApiError ? err.message : 'Something went wrong. Please try again.'
}

// Generic skeleton — used for every manager page's initial load, whether
// it ends up rendering a table or a card list, so it deliberately doesn't
// try to mimic either shape exactly (row-of-avatar-plus-two-bars reads
// fine as a stand-in for both).
export function LoadingState({ label, rows = 5 }) {
  return <div className="card-k mt-7 overflow-hidden" role="status" aria-label={`Loading ${label}`}>
    <div className="divide-y divide-kBorderSoft">
      {Array.from({ length: rows }, (_, i) => <div key={i} className="flex items-center gap-4 p-5">
        <div className="h-10 w-10 shrink-0 animate-pulse rounded-full bg-kBorderSoft" />
        <div className="grid flex-1 gap-2">
          <div className="h-3.5 w-1/3 animate-pulse rounded-full bg-kBorderSoft" />
          <div className="h-3 w-1/2 animate-pulse rounded-full bg-kBorderSoft" />
        </div>
        <div className="h-6 w-16 shrink-0 animate-pulse rounded-full bg-kBorderSoft" />
      </div>)}
    </div>
  </div>
}

export function ErrorState({ message, onRetry }) {
  return <div className="card-k mt-7 p-10 text-center">
    <div className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-red-500/10 text-red-500"><AlertCircle size={22} /></div>
    <p className="mt-4 text-sm font-semibold text-kInk">{message}</p>
    <button onClick={onRetry} className="btn-orange mx-auto mt-5">Try again</button>
  </div>
}

export function EmptyState({ icon: Icon, title, message, action }) {
  return <div className="card-k mt-7 p-10 text-center">
    {Icon && <div className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-kTint text-kOrange"><Icon size={22} /></div>}
    {title && <p className="mt-4 text-sm font-bold text-kInk">{title}</p>}
    {message && <p className={`text-sm text-kMuted ${title ? 'mt-1' : ''}`}>{message}</p>}
    {action && <div className="mt-5">{action}</div>}
  </div>
}

export function timeAgo(iso) {
  const seconds = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  if (seconds < 60) return 'just now'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}
