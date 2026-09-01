import { useCallback, useEffect, useState } from 'react'
import { Laptop, LogOut, ShieldX } from 'lucide-react'
import Shell from '../../components/admin/Shell'
import { LoadingState, ErrorState, EmptyState, errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch } from '../../lib/api'

function SessionCard({ session, onRevoke, busy }) {
  return <div className={`card-k flex items-center justify-between gap-4 p-5 ${session.is_current ? 'border-kGreen' : ''}`}>
    <div className="flex items-center gap-3">
      <div className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-kTint text-kGreen"><Laptop size={18} /></div>
      <div>
        <div className="flex items-center gap-2 text-sm font-semibold text-kInk">
          {session.user_agent || 'Unknown device'}
          {session.is_current && <span className="rounded-full bg-kGreen/10 px-2 py-0.5 text-xs font-bold text-kGreen">This device</span>}
        </div>
        <div className="text-xs text-kMuted">{session.ip_address || 'Unknown location'} &middot; last active {new Date(session.last_seen_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}</div>
      </div>
    </div>
    {!session.is_current && (
      <button disabled={busy} onClick={() => onRevoke(session.id)} className="shrink-0 text-xs font-bold text-red-500 hover:underline disabled:opacity-60">Sign out</button>
    )}
  </div>
}

export default function SessionsManager({ showToast }) {
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try { setSessions((await apiFetch('/api/sessions')).sessions) }
    catch (err) { setError(errorMessage(err)) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  async function revokeOne(id) {
    setBusy(true)
    try { await apiFetch(`/api/sessions/${id}`, { method: 'DELETE' }); showToast('Device signed out'); load() }
    catch (err) { showToast(errorMessage(err)) }
    finally { setBusy(false) }
  }

  async function revokeOthers() {
    if (!window.confirm('Sign out every other device? This one stays signed in.')) return
    setBusy(true)
    try { const res = await apiFetch('/api/sessions/revoke-others', { method: 'POST' }); showToast(`Signed out ${res.revoked_count} other device(s)`); load() }
    catch (err) { showToast(errorMessage(err)) }
    finally { setBusy(false) }
  }

  async function revokeAll() {
    if (!window.confirm('Sign out everywhere, including this device? You will need to log in again.')) return
    setBusy(true)
    try {
      await apiFetch('/api/sessions/revoke-all', { method: 'POST' })
      showToast('Signed out everywhere')
      window.location.href = '/admin/login'
    } catch (err) { showToast(errorMessage(err)); setBusy(false) }
  }

  return <Shell>
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div><div className="eyebrow">Administration</div><h1 className="font-display text-3xl font-bold text-kGreen">Sessions</h1></div>
      {!loading && !error && sessions.length > 1 && (
        <div className="flex gap-2">
          <button disabled={busy} onClick={revokeOthers} className="flex items-center gap-1.5 rounded-xl border border-kBorderSoft px-3 py-2 text-xs font-bold text-kInk hover:bg-kTint disabled:opacity-60"><LogOut size={14} /> Sign out other devices</button>
          <button disabled={busy} onClick={revokeAll} className="flex items-center gap-1.5 rounded-xl border border-red-200 px-3 py-2 text-xs font-bold text-red-500 hover:bg-red-50 disabled:opacity-60"><ShieldX size={14} /> Sign out everywhere</button>
        </div>
      )}
    </div>
    <p className="mt-2 max-w-2xl text-sm text-kMuted">Every device currently signed in to your account. Signing a device out here immediately invalidates it — it cannot renew its session again.</p>

    <div className="mt-6 grid gap-3">
      {loading && <LoadingState label="sessions" rows={2} />}
      {!loading && error && <ErrorState message={error} onRetry={load} />}
      {!loading && !error && sessions.length === 0 && <EmptyState icon={Laptop} title="No active sessions" message="You're not signed in anywhere right now." />}
      {!loading && !error && sessions.map(s => <SessionCard key={s.id} session={s} onRevoke={revokeOne} busy={busy} />)}
    </div>
  </Shell>
}
