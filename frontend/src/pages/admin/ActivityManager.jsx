import { useState, useEffect, useCallback } from 'react'
import { Search, Plus, Users } from 'lucide-react'
import Shell from '../../components/admin/Shell'
import Modal from '../../components/admin/Modal'
import { LoadingState, ErrorState, errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch } from '../../lib/api'

const ACTIVITY_TYPES = ['Exercise', 'Walking', 'Games', 'Social', 'Intergenerational', 'Skills Training', 'Educational', 'Community Event', 'Other']
const STATUSES = ['Scheduled', 'In Progress', 'Completed', 'Cancelled']
const PARTICIPANT_STATUSES = ['Registered', 'Attended', 'No-show', 'Cancelled']
const PARTICIPANT_STYLES = { Registered: 'bg-kBorderSoft text-kMuted', Attended: 'bg-kGreen/10 text-kGreen', 'No-show': 'bg-red-100 text-red-700', Cancelled: 'bg-kBorderSoft text-kMuted' }

function fmt(iso) { return new Date(iso).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }) }
function toLocalInput(iso) { return iso ? new Date(iso).toISOString().slice(0, 16) : '' }

function NewActivityModal({ onClose, onCreated, showToast }) {
  const [saving, setSaving] = useState(false)
  async function save(e) {
    e.preventDefault()
    const f = new FormData(e.target)
    setSaving(true)
    try {
      await onCreated({
        title: f.get('title'), activity_type: f.get('activity_type'),
        scheduled_at: new Date(f.get('scheduled_at')).toISOString(),
        location: f.get('location') || null, description: f.get('description') || null,
      })
      showToast('Activity created')
      onClose()
    } catch (err) { showToast(errorMessage(err)) }
    finally { setSaving(false) }
  }
  return <Modal title="Create activity" onClose={onClose}>
    <form onSubmit={save} className="grid gap-4">
      <label className="text-sm font-semibold">Title<input name="title" className="input-k mt-2" required /></label>
      <div className="grid grid-cols-2 gap-4">
        <label className="text-sm font-semibold">Type<select name="activity_type" defaultValue="Social" className="input-k mt-2">{ACTIVITY_TYPES.map(t => <option key={t}>{t}</option>)}</select></label>
        <label className="text-sm font-semibold">Date &amp; time<input name="scheduled_at" type="datetime-local" className="input-k mt-2" required /></label>
      </div>
      <label className="text-sm font-semibold">Location<input name="location" className="input-k mt-2" /></label>
      <label className="text-sm font-semibold">Description<textarea name="description" rows={2} className="input-k mt-2" /></label>
      <button disabled={saving} className="btn-orange mt-2 disabled:opacity-60">{saving ? 'Creating…' : 'Create activity'}</button>
    </form>
  </Modal>
}

function ParticipantsPanel({ activity, onChanged, showToast }) {
  const [members, setMembers] = useState([])
  const [participants, setParticipants] = useState([])
  const [loading, setLoading] = useState(true)
  const [q, setQ] = useState('')
  const [busyId, setBusyId] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [membersRes, participantsRes] = await Promise.all([
        apiFetch('/api/elderly'),
        apiFetch(`/api/activities/${activity.id}/participants`),
      ])
      setMembers(membersRes.members)
      setParticipants(participantsRes.participants)
    } catch (err) { showToast(errorMessage(err)) }
    finally { setLoading(false) }
  }, [activity.id, showToast])

  useEffect(() => { load() }, [load])

  const registeredIds = new Set(participants.map(p => p.elderly_member_id))
  const query = q.trim().toLowerCase()
  const results = query
    ? members.filter(m => !registeredIds.has(m.id) && (m.full_name.toLowerCase().includes(query) || m.member_id.toLowerCase().includes(query))).slice(0, 8)
    : []

  async function register(member) {
    setBusyId(member.id)
    try {
      await apiFetch(`/api/activities/${activity.id}/participants`, { method: 'POST', body: { elderly_member_id: member.id } })
      showToast(`${member.full_name} registered`)
      setQ('')
      load()
      onChanged()
    } catch (err) { showToast(errorMessage(err)) }
    finally { setBusyId(null) }
  }

  async function setStatus(participant, status) {
    try {
      await apiFetch(`/api/activities/${activity.id}/participants/${participant.id}`, { method: 'PATCH', body: { status } })
      showToast(`${participant.elderly_member_name} marked ${status}`)
      load()
    } catch (err) { showToast(errorMessage(err)) }
  }

  return <div className="card-k mt-6 p-6">
    <div className="flex items-center justify-between"><h2 className="font-display text-lg font-bold text-kGreen">{activity.title}</h2><div className="flex items-center gap-2 text-sm font-semibold text-kMuted"><Users size={16} /> {participants.length}</div></div>
    <p className="mt-1 text-xs text-kMuted">{activity.activity_type} &middot; {fmt(activity.scheduled_at)}{activity.location ? ` · ${activity.location}` : ''}</p>

    <div className="relative mt-5"><Search className="absolute left-3 top-3.5 text-kMuted" size={17} /><input value={q} onChange={e => setQ(e.target.value)} className="input-k pl-10" placeholder="Search a member to register..." /></div>
    {query && <div className="mt-3 grid gap-2">
      {results.length === 0 && <p className="text-sm text-kMuted">No matching member.</p>}
      {results.map(m => <div key={m.id} className="flex items-center justify-between rounded-xl border border-kBorder px-4 py-3">
        <div className="text-sm font-semibold text-kInk">{m.full_name} <span className="font-normal text-kMuted">({m.member_id})</span></div>
        <button disabled={busyId === m.id} onClick={() => register(m)} className="btn-green disabled:opacity-60">Register</button>
      </div>)}
    </div>}

    {loading ? <p className="mt-4 text-sm text-kMuted">Loading…</p> : <div className="mt-5 grid gap-2">
      {participants.map(p => <div key={p.id} className="flex flex-wrap items-center justify-between gap-2 rounded-xl bg-kCream px-4 py-3">
        <div><span className="text-sm font-semibold text-kInk">{p.elderly_member_name}</span> <span className="text-xs text-kMuted">({p.elderly_member_code})</span></div>
        <select value={p.status} onChange={e => setStatus(p, e.target.value)} className={`rounded-full border-none px-3 py-1 text-xs font-bold ${PARTICIPANT_STYLES[p.status]}`}>{PARTICIPANT_STATUSES.map(s => <option key={s}>{s}</option>)}</select>
      </div>)}
      {participants.length === 0 && <p className="text-sm text-kMuted">No one registered yet.</p>}
    </div>}
  </div>
}

export default function ActivityManager({ showToast }) {
  const [activities, setActivities] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [typeFilter, setTypeFilter] = useState('All')
  const [statusFilter, setStatusFilter] = useState('All')
  const [selected, setSelected] = useState(null)
  const [newModalOpen, setNewModalOpen] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const params = new URLSearchParams()
      if (typeFilter !== 'All') params.set('activity_type', typeFilter)
      if (statusFilter !== 'All') params.set('status', statusFilter)
      const data = await apiFetch(`/api/activities?${params.toString()}`)
      setActivities(data.activities)
      setSelected(prev => prev ? data.activities.find(a => a.id === prev.id) || null : null)
    } catch (err) { setError(errorMessage(err)) }
    finally { setLoading(false) }
  }, [typeFilter, statusFilter])

  useEffect(() => { load() }, [load])

  return <Shell>
    <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
      <div><div className="eyebrow">Manage</div><h1 className="font-display text-3xl font-bold text-kGreen">Activities</h1></div>
      <button onClick={() => setNewModalOpen(true)} className="btn-green"><Plus size={16} /> Create activity</button>
    </div>

    <div className="mt-7 grid gap-6 xl:grid-cols-[1fr_1.1fr]">
      <div>
        <div className="card-k overflow-hidden">
          <div className="flex flex-col gap-3 border-b border-kBorderSoft p-5 sm:flex-row">
            <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)} className="flex-1 rounded-xl border border-kBorder bg-kSurface px-4 py-3 text-sm text-kInk"><option>All</option>{ACTIVITY_TYPES.map(t => <option key={t}>{t}</option>)}</select>
            <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="flex-1 rounded-xl border border-kBorder bg-kSurface px-4 py-3 text-sm text-kInk"><option>All</option>{STATUSES.map(s => <option key={s}>{s}</option>)}</select>
          </div>
          {loading ? <LoadingState label="activities" /> : error ? <ErrorState message={error} onRetry={load} /> : <div className="grid gap-2 p-4">
            {activities.map(a => <button key={a.id} onClick={() => setSelected(a)} className={`flex items-center justify-between rounded-xl border px-4 py-3 text-left ${selected?.id === a.id ? 'border-kOrange bg-kTint' : 'border-kBorder hover:bg-kCream'}`}>
              <div><div className="font-semibold text-kInk">{a.title}</div><div className="text-xs text-kMuted">{a.activity_type} &middot; {fmt(a.scheduled_at)}</div></div>
              <div className="flex items-center gap-1 text-xs font-bold text-kOrange"><Users size={14} /> {a.participant_count}</div>
            </button>)}
            {activities.length === 0 && <p className="p-4 text-center text-sm text-kMuted">No activities match your filters.</p>}
          </div>}
        </div>
      </div>
      <div>{selected ? <ParticipantsPanel activity={selected} onChanged={load} showToast={showToast} /> : <div className="card-k p-10 text-center text-sm text-kMuted">Select an activity to manage participants.</div>}</div>
    </div>

    {newModalOpen && <NewActivityModal onClose={() => setNewModalOpen(false)} onCreated={async data => { await apiFetch('/api/activities', { method: 'POST', body: data }); load() }} showToast={showToast} />}
  </Shell>
}
