import { useState, useEffect, useCallback } from 'react'
import { Laptop, Plus, Trash2 } from 'lucide-react'
import VolunteerShell from '../../components/volunteer/VolunteerShell'
import { LoadingState, ErrorState, errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch } from '../../lib/api'

const STATUS_COPY = {
  Pending: 'Your profile is awaiting review by KDCCE staff.',
  Verified: "You're verified — staff can now assign you to home visits and activities.",
  Rejected: 'Your volunteer application was not approved. Contact KDCCE staff with any questions.',
}
const STATUS_STYLES = {
  Pending: 'bg-kTint text-kOrange',
  Verified: 'bg-kGreen/10 text-kGreen',
  Rejected: 'bg-red-100 text-red-700',
}
const DAYS_OF_WEEK = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

function AvailabilityPanel({ showToast }) {
  const [slots, setSlots] = useState([])
  const [ranges, setRanges] = useState([])
  const [loading, setLoading] = useState(true)
  const [addingSlot, setAddingSlot] = useState(false)
  const [addingRange, setAddingRange] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [a, u] = await Promise.all([apiFetch('/api/volunteers/me/availability'), apiFetch('/api/volunteers/me/unavailability')])
      setSlots(a.availability)
      setRanges(u.unavailability)
    } catch (err) { showToast(errorMessage(err)) }
    finally { setLoading(false) }
  }, [showToast])

  useEffect(() => { load() }, [load])

  async function addSlot(e) {
    e.preventDefault()
    const f = new FormData(e.target)
    setAddingSlot(true)
    try {
      await apiFetch('/api/volunteers/me/availability', { method: 'POST', body: { day_of_week: f.get('day_of_week'), start_time: f.get('start_time'), end_time: f.get('end_time') } })
      e.target.reset()
      load()
    } catch (err) { showToast(errorMessage(err)) }
    finally { setAddingSlot(false) }
  }

  async function removeSlot(id) {
    try { await apiFetch(`/api/volunteers/me/availability/${id}`, { method: 'DELETE' }); load() }
    catch (err) { showToast(errorMessage(err)) }
  }

  async function addRange(e) {
    e.preventDefault()
    const f = new FormData(e.target)
    setAddingRange(true)
    try {
      await apiFetch('/api/volunteers/me/unavailability', { method: 'POST', body: { start_date: f.get('start_date'), end_date: f.get('end_date'), reason: f.get('reason') || null } })
      e.target.reset()
      load()
    } catch (err) { showToast(errorMessage(err)) }
    finally { setAddingRange(false) }
  }

  async function removeRange(id) {
    try { await apiFetch(`/api/volunteers/me/unavailability/${id}`, { method: 'DELETE' }); load() }
    catch (err) { showToast(errorMessage(err)) }
  }

  if (loading) return <div className="card-k mt-6 p-6 text-sm text-kMuted">Loading availability…</div>

  return <div className="card-k mt-6 grid gap-6 p-6">
    <div>
      <h2 className="font-display text-lg font-bold text-kGreen">Weekly availability</h2>
      <p className="mt-1 text-sm text-kMuted">Let staff know which windows you're usually free for — this is separate from the free-text note above and helps when they're deciding who to assign.</p>
      <div className="mt-4 grid gap-2">
        {slots.map(s => <div key={s.id} className="flex items-center justify-between rounded-xl bg-kCream px-4 py-3">
          <span className="text-sm font-semibold text-kInk">{s.day_of_week} &middot; {s.start_time}–{s.end_time}</span>
          <button onClick={() => removeSlot(s.id)} className="text-kMuted hover:text-red-600"><Trash2 size={16} /></button>
        </div>)}
        {slots.length === 0 && <p className="text-sm text-kMuted">No weekly windows added yet.</p>}
      </div>
      <form onSubmit={addSlot} className="mt-4 flex flex-wrap items-end gap-3">
        <label className="text-xs font-semibold">Day<select name="day_of_week" className="input-k mt-1" required>{DAYS_OF_WEEK.map(d => <option key={d}>{d}</option>)}</select></label>
        <label className="text-xs font-semibold">From<input name="start_time" type="time" defaultValue="09:00" className="input-k mt-1" required /></label>
        <label className="text-xs font-semibold">To<input name="end_time" type="time" defaultValue="12:00" className="input-k mt-1" required /></label>
        <button disabled={addingSlot} className="btn-orange disabled:opacity-60"><Plus size={15} /> Add</button>
      </form>
    </div>

    <div className="border-t border-kBorderSoft pt-6">
      <h2 className="font-display text-lg font-bold text-kGreen">Unavailable dates</h2>
      <p className="mt-1 text-sm text-kMuted">Planning to be away? Flag the date range so staff know not to schedule you then.</p>
      <div className="mt-4 grid gap-2">
        {ranges.map(r => <div key={r.id} className="flex items-center justify-between rounded-xl bg-kCream px-4 py-3">
          <span className="text-sm font-semibold text-kInk">{r.start_date} to {r.end_date}{r.reason ? ` — ${r.reason}` : ''}</span>
          <button onClick={() => removeRange(r.id)} className="text-kMuted hover:text-red-600"><Trash2 size={16} /></button>
        </div>)}
        {ranges.length === 0 && <p className="text-sm text-kMuted">No unavailable dates flagged.</p>}
      </div>
      <form onSubmit={addRange} className="mt-4 flex flex-wrap items-end gap-3">
        <label className="text-xs font-semibold">From<input name="start_date" type="date" className="input-k mt-1" required /></label>
        <label className="text-xs font-semibold">To<input name="end_date" type="date" className="input-k mt-1" required /></label>
        <label className="text-xs font-semibold">Reason (optional)<input name="reason" className="input-k mt-1" placeholder="e.g. Travel" /></label>
        <button disabled={addingRange} className="btn-orange disabled:opacity-60"><Plus size={15} /> Add</button>
      </form>
    </div>
  </div>
}

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

  async function signOutOthers() {
    setBusy(true)
    try { const res = await apiFetch('/api/sessions/revoke-others', { method: 'POST' }); showToast(`Signed out ${res.revoked_count} other device(s)`); load() }
    catch (err) { showToast(errorMessage(err)) }
    finally { setBusy(false) }
  }

  if (loading) return <div className="card-k mt-6 p-6 text-sm text-kMuted">Loading account security…</div>

  return <div className="card-k mt-6 grid gap-6 p-6">
    <div>
      <div className="flex items-center justify-between">
        <h2 className="font-display text-lg font-bold text-kGreen">Signed-in devices</h2>
        {sessions.length > 1 && <button disabled={busy} onClick={signOutOthers} className="text-xs font-bold text-kOrange disabled:opacity-60">Sign out other devices</button>}
      </div>
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

export default function MyVolunteerProfile({ showToast }) {
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try { setProfile((await apiFetch('/api/volunteers/me')).volunteer) }
    catch (err) { setError(errorMessage(err)) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  async function save(e) {
    e.preventDefault()
    const f = new FormData(e.target)
    const data = {
      phone: f.get('phone') || null,
      skills: f.get('skills') || null,
      availability: f.get('availability') || null,
      areas_of_interest: f.get('areas_of_interest') || null,
      experience: f.get('experience') || null,
      motivation: f.get('motivation') || null,
      bio: f.get('bio') || null,
    }
    setSaving(true)
    try {
      const res = await apiFetch('/api/volunteers/me', { method: 'PATCH', body: data })
      setProfile(res.volunteer)
      showToast('Profile updated')
    } catch (err) { showToast(errorMessage(err)) }
    finally { setSaving(false) }
  }

  return <VolunteerShell>
    <div><div className="eyebrow">My account</div><h1 className="font-display text-3xl font-bold text-kGreen">My volunteer profile</h1></div>

    {loading ? <LoadingState label="profile" /> : error ? <ErrorState message={error} onRetry={load} /> : <>
      <div className="card-k mt-7 p-6">
        <span className={`rounded-full px-3 py-1 text-xs font-bold ${STATUS_STYLES[profile.status]}`}>{profile.status}</span>
        <p className="mt-3 text-sm text-kMuted">{STATUS_COPY[profile.status]}</p>
      </div>

      <form onSubmit={save} className="card-k mt-6 grid gap-4 p-6">
        <h2 className="font-display text-lg font-bold text-kGreen">Your details</h2>
        <label className="text-sm font-semibold">Phone<input name="phone" defaultValue={profile.phone || ''} className="input-k mt-2" /></label>
        <label className="text-sm font-semibold">Skills<textarea name="skills" defaultValue={profile.skills || ''} rows={2} className="input-k mt-2" placeholder="e.g. First aid, cooking, transport" /></label>
        <label className="text-sm font-semibold">Availability<textarea name="availability" defaultValue={profile.availability || ''} rows={2} className="input-k mt-2" placeholder="e.g. Weekday mornings" /></label>
        <label className="text-sm font-semibold">Areas of interest<textarea name="areas_of_interest" defaultValue={profile.areas_of_interest || ''} rows={2} className="input-k mt-2" placeholder="e.g. Elderly care, home visits, companionship" /></label>
        <label className="text-sm font-semibold">Experience<textarea name="experience" defaultValue={profile.experience || ''} rows={2} className="input-k mt-2" /></label>
        <label className="text-sm font-semibold">Motivation<textarea name="motivation" defaultValue={profile.motivation || ''} rows={2} className="input-k mt-2" placeholder="Why you want to volunteer with KDCCE" /></label>
        <label className="text-sm font-semibold">About you<textarea name="bio" defaultValue={profile.bio || ''} rows={3} className="input-k mt-2" /></label>
        <button disabled={saving} className="btn-orange mt-2 w-fit disabled:opacity-60">{saving ? 'Saving…' : 'Save changes'}</button>
      </form>

      <AvailabilityPanel showToast={showToast} />
      <SecurityPanel showToast={showToast} />
    </>}
  </VolunteerShell>
}
