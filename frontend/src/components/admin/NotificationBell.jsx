import { useState, useEffect, useCallback, useRef } from 'react'
import { Bell, Check } from 'lucide-react'
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

export default function NotificationBell({ variant = 'dark' }) {
  const [open, setOpen] = useState(false)
  const [unreadCount, setUnreadCount] = useState(0)
  const [notifications, setNotifications] = useState([])
  const [loading, setLoading] = useState(false)
  const panelRef = useRef(null)

  const loadUnreadCount = useCallback(async () => {
    try { setUnreadCount((await apiFetch('/api/notifications/unread-count')).unread_count) }
    catch { /* silent — a failed badge refresh shouldn't disrupt the page */ }
  }, [])

  const loadList = useCallback(async () => {
    setLoading(true)
    try { setNotifications((await apiFetch('/api/notifications?per_page=8')).notifications) }
    catch { /* silent */ }
    finally { setLoading(false) }
  }, [])

  useEffect(() => {
    loadUnreadCount()
    const interval = setInterval(loadUnreadCount, 60000)
    return () => clearInterval(interval)
  }, [loadUnreadCount])

  useEffect(() => {
    if (open) loadList()
  }, [open, loadList])

  async function markRead(notification) {
    try {
      await apiFetch(`/api/notifications/${notification.id}`, { method: 'PATCH', body: { is_read: true } })
      setNotifications(prev => prev.map(n => n.id === notification.id ? { ...n, is_read: true } : n))
      loadUnreadCount()
    } catch { /* silent */ }
  }

  async function markAllRead() {
    try {
      await apiFetch('/api/notifications/mark-all-read', { method: 'POST' })
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })))
      setUnreadCount(0)
    } catch { /* silent */ }
  }

  const iconClass = variant === 'dark' ? 'text-white/70 hover:text-white' : 'text-kMuted hover:text-kInk'

  return <div className="relative">
    <button onClick={() => setOpen(o => !o)} className={`relative grid h-9 w-9 place-items-center rounded-full hover:bg-white/10 ${iconClass}`} aria-label="Notifications">
      <Bell size={18} />
      {unreadCount > 0 && <span className="absolute -right-0.5 -top-0.5 grid h-4 min-w-[16px] place-items-center rounded-full bg-kOrange px-1 text-[10px] font-bold text-white">{unreadCount > 9 ? '9+' : unreadCount}</span>}
    </button>
    {open && <div ref={panelRef} className="absolute right-0 z-30 mt-2 w-80 overflow-hidden rounded-2xl border border-kBorderSoft bg-kSurface text-kInk shadow-soft" onMouseLeave={() => setOpen(false)}>
      <div className="flex items-center justify-between border-b border-kBorderSoft px-4 py-3"><span className="text-sm font-bold text-kGreen">Notifications</span>{unreadCount > 0 && <button onClick={markAllRead} className="flex items-center gap-1 text-xs font-semibold text-kOrange"><Check size={13} /> Mark all read</button>}</div>
      <div className="max-h-96 overflow-y-auto">
        {loading ? <p className="p-4 text-center text-sm text-kMuted">Loading…</p> : notifications.length === 0 ? <p className="p-4 text-center text-sm text-kMuted">No notifications yet.</p> : notifications.map(n => <button key={n.id} onClick={() => markRead(n)} className={`block w-full border-b border-kBorderSoft px-4 py-3 text-left last:border-0 ${n.is_read ? '' : 'bg-kTint/40'}`}>
          <div className="flex items-start justify-between gap-2"><span className="text-sm font-semibold text-kInk">{n.title}</span>{!n.is_read && <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-kOrange" />}</div>
          <p className="mt-1 text-xs text-kMuted">{n.message}</p>
          <p className="mt-1 text-[10px] uppercase tracking-wide text-kMuted">{timeAgo(n.created_at)}</p>
        </button>)}
      </div>
    </div>}
  </div>
}
