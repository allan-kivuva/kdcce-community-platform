import { useState } from 'react'
import { ApiError } from '../../lib/api'

export function useToast() {
  const [toast, setToast] = useState('')
  function show(message) { setToast(message); window.clearTimeout(show._t); show._t = window.setTimeout(() => setToast(''), 2200) }
  return [toast, show]
}

export function errorMessage(err) {
  return err instanceof ApiError ? err.message : 'Something went wrong. Please try again.'
}

export function LoadingState({ label }) { return <div className="card-k mt-7 p-10 text-center text-sm text-kMuted">Loading {label}…</div> }
export function ErrorState({ message, onRetry }) { return <div className="card-k mt-7 p-10 text-center"><p className="text-sm text-kOrange">{message}</p><button onClick={onRetry} className="mt-4 text-sm font-bold text-kGreen">Try again</button></div> }
