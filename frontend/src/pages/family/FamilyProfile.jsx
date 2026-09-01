import { useState, useEffect, useCallback } from 'react'
import { Laptop, UserRound } from 'lucide-react'
import FamilyShell from '../../components/family/FamilyShell'
import { LoadingState, errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch, getStoredUser } from '../../lib/api'

function SecurityPanel({ showToast }) {
  const [sessions, setSessions] = useState([])
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [s, h] = await Promise.all([apiFetch('/api/sessions'), apiFetch('/api/users/me/login-history')])
      setSessions(s.sessions)
      setHistory(h.login_history)
    } catch (err) { showToast(errorMessage(err)) }
    finally { setLoading(false) }
  }, [showToast])

  useEffect(() => { load() }, [load])

  async function revoke(id) {
    setBusy(true)
    try { await apiFetch(`/api/sessions/${id}`, { method: 'DELETE' }); load() }
    catch (err) { showToast(errorMessage(err)) }
    finally { setBusy(false) }
  }

  if (loading) return <div className="card-k mt-6 p-6 text-sm text-kMuted">Loading account security…</div>

  return <div className="card-k mt-6 grid gap-6 p-6">
    <div>
      <h2 className="font-display text-lg font-bold text-kGreen">Signed-in devices</h2>
      <div className="mt-4 grid gap-2">
        {sessions.map(s => <div key={s.id} className="flex items-center justify-between rounded-xl bg-kCream px-4 py-3">
          <span className="flex items-center gap-2 text-sm font-semibold text-kInk"><Laptop size={15} /> {s.user_agent || 'Unknown device'}{s.is_current ? ' (this device)' : ''}</span>
          {!s.is_current && <button disabled={busy} onClick={() => revoke(s.id)} className="text-xs font-bold text-red-500 disabled:opacity-60">Sign out</button>}
        </div>)}
        {sessions.length === 0 && <p className="text-sm text-kMuted">No active sessions.</p>}
      </div>
    </div>
    <div className="border-t border-kBorderSoft pt-6">
      <h2 className="font-display text-lg font-bold text-kGreen">Recent logins</h2>
      <div className="mt-4 grid gap-2">
        {history.slice(0, 5).map(h => <div key={h.id} className="flex items-center justify-between rounded-xl bg-kCream px-4 py-3 text-sm">
          <span className={h.success ? 'font-semibold text-kInk' : 'font-semibold text-red-500'}>{h.success ? 'Successful login' : `Failed login (${h.failure_reason || 'unknown reason'})`}</span>
          <span className="text-xs text-kMuted">{new Date(h.created_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}</span>
        </div>)}
        {history.length === 0 && <p className="text-sm text-kMuted">No login history yet.</p>}
      </div>
    </div>
  </div>
}

export default function FamilyProfile({ showToast }) {
  const user = getStoredUser()
  const [members, setMembers] = useState(null)

  useEffect(() => { apiFetch('/api/family/members').then(d => setMembers(d.members)).catch(() => setMembers([])) }, [])

  return <FamilyShell>
    <div><div className="eyebrow">Your account</div><h1 className="font-display text-3xl font-bold text-kGreen">Profile &amp; Security</h1></div>

    <div className="card-k mt-7 p-6">
      <div className="flex items-center gap-3">
        <div className="grid h-12 w-12 place-items-center rounded-full bg-kTint text-kOrange"><UserRound size={20} /></div>
        <div><div className="font-semibold text-kInk">{user?.name}</div><div className="text-sm text-kMuted">{user?.email}</div></div>
      </div>
      <div className="mt-5 border-t border-kBorderSoft pt-5">
        <div className="text-xs font-bold uppercase tracking-wide text-kMuted">Linked family members</div>
        {members === null ? <LoadingState label="linked members" rows={1} /> : (
          <div className="mt-3 grid gap-2">
            {members.map(m => <div key={m.id} className="rounded-xl bg-kCream px-4 py-3 text-sm"><span className="font-semibold text-kInk">{m.full_name}</span> <span className="text-kMuted">— {m.relationship}</span></div>)}
            {members.length === 0 && <p className="text-sm text-kMuted">No linked members yet.</p>}
          </div>
        )}
      </div>
    </div>

    <SecurityPanel showToast={showToast} />
  </FamilyShell>
}
