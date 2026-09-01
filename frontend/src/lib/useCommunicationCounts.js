import { useState, useEffect, useCallback } from 'react'
import { apiFetch } from './api'

/** One shared 60-second poll for unread direct-message count (+ needs-reply
 * count for admin/staff) — used by both Shell (admin nav badge) and
 * VolunteerShell (volunteer nav badge) so no page polls independently.
 * `role` gates the extra unresolved-count call to admin/staff, since a
 * volunteer's token would just 403 on it. Mirrors NotificationBell's own
 * 60s interval pattern (same interval, same silent-failure-on-badge
 * philosophy — a failed poll just leaves the badge at its last value). */
export function useCommunicationCounts(role) {
  const [unreadMessages, setUnreadMessages] = useState(0)
  const [needsReplyCount, setNeedsReplyCount] = useState(0)

  const refresh = useCallback(async () => {
    try { setUnreadMessages((await apiFetch('/api/messages/unread-count')).unread_count) }
    catch { /* silent — a failed badge refresh shouldn't disrupt the page */ }

    if (role === 'admin' || role === 'staff') {
      try { setNeedsReplyCount((await apiFetch('/api/messages/unresolved')).unresolved.length) }
      catch { /* silent */ }
    }
  }, [role])

  useEffect(() => {
    refresh()
    const interval = setInterval(refresh, 60000)
    return () => clearInterval(interval)
  }, [refresh])

  return { unreadMessages, needsReplyCount, refresh }
}
