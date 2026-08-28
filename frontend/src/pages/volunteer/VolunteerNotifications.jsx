import { useState, useEffect, useCallback } from 'react'
import { Bell, BellRing, Check } from 'lucide-react'
import VolunteerShell from '../../components/volunteer/VolunteerShell'
import { LoadingState, ErrorState, errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch } from '../../lib/api'

function timeAgo(iso) {
  const seconds = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  if (seconds < 60) return 'just now'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}

export default function VolunteerNotifications() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try { setItems((await apiFetch('/api/notifications?per_page=50')).notifications) }
    catch (err) { setError(errorMessage(err)) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  async function markRead(n) {
    if (n.is_read) return
    try {
      await apiFetch(`/api/notifications/${n.id}`, { method: 'PATCH', body: { is_read: true } })
      setItems(prev => prev.map(x => x.id === n.id ? { ...x, is_read: true } : x))
    } catch { /* non-critical */ }
  }

  async function markAllRead() {
    try {
      await apiFetch('/api/notifications/mark-all-read', { method: 'POST' })
      setItems(prev => prev.map(x => ({ ...x, is_read: true })))
    } catch { /* non-critical */ }
  }

  const unread = items.filter(n => !n.is_read).length

  return <VolunteerShell>
    <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center"><div><div className="eyebrow">Stay updated</div><h1 className="font-display text-3xl font-bold text-kGreen">Notifications</h1></div>{unread > 0 && <button onClick={markAllRead} className="flex items-center gap-2 rounded-full bg-kTint px-4 py-2 text-sm font-bold text-kOrange"><Check size={14} /> Mark all read</button>}</div>

    {loading ? <LoadingState label="notifications" /> : error ? <ErrorState message={error} onRetry={load} /> : <div className="card-k mt-7 divide-y divide-kBorderSoft">
      {items.map(n => <button key={n.id} onClick={() => markRead(n)} className={`block w-full p-5 text-left ${n.is_read ? '' : 'bg-kTint/40'}`}>
        <div className="flex items-start gap-3">
          {n.is_read ? <Bell size={18} className="mt-0.5 shrink-0 text-kMuted" /> : <BellRing size={18} className="mt-0.5 shrink-0 text-kOrange" />}
          <div className="flex-1"><div className={`text-sm ${n.is_read ? 'font-semibold text-kInk' : 'font-bold text-kGreen'}`}>{n.title}</div><p className="mt-1 text-sm text-kMuted">{n.message}</p><p className="mt-1 text-xs uppercase tracking-wide text-kMuted">{timeAgo(n.created_at)}</p></div>
        </div>
      </button>)}
      {items.length === 0 && <p className="p-10 text-center text-sm text-kMuted">No notifications yet.</p>}
    </div>}
  </VolunteerShell>
}
