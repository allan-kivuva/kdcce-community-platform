import { useState, useEffect, useCallback } from 'react'
import { Search, Plus, Users, UserCheck, Clock, LogIn, LogOut } from 'lucide-react'
import Shell from '../../components/admin/Shell'
import Modal from '../../components/admin/Modal'
import StatusBadge from '../../components/admin/StatusBadge'
import { LoadingState, ErrorState, errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch } from '../../lib/api'

const ACTIVITY_TYPES = ['Exercise', 'Walking', 'Games', 'Social', 'Intergenerational', 'Skills Training', 'Educational', 'Community Event', 'Other']
const STATUSES = ['Scheduled', 'In Progress', 'Completed', 'Cancelled']
const PARTICIPANT_STATUSES = ['Registered', 'Attended', 'No-show', 'Cancelled']
const PARTICIPANT_STYLES = { Registered: 'bg-kBorderSoft text-kMuted', Attended: 'bg-kGreen/10 text-kGreen', 'No-show': 'bg-red-100 text-red-700', Cancelled: 'bg-kBorderSoft text-kMuted' }
const VOLUNTEER_ROLES = ['Facilitator', 'Support', 'Registration', 'Logistics', 'General Volunteer']
const VOLUNTEER_STATUSES = ['Assigned', 'Confirmed', 'Waitlisted', 'Declined', 'Cancelled', 'Attended', 'No Show']

function fmt(iso) { return new Date(iso).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }) }
function toLocalInput(iso) { return iso ? new Date(iso).toISOString().slice(0, 16) : '' }

function ActivityFormModal({ activity, onClose, onSaved, showToast }) {
  const [saving, setSaving] = useState(false)
  const [programs, setPrograms] = useState([])
  const isEdit = !!activity

  useEffect(() => { apiFetch('/api/programs').then(d => setPrograms(d.programs)).catch(() => {}) }, [])

  async function save(e) {
    e.preventDefault()
    const f = new FormData(e.target)
    setSaving(true)
    try {
      const body = {
        title: f.get('title'), activity_type: f.get('activity_type'),
        scheduled_at: new Date(f.get('scheduled_at')).toISOString(),
        location: f.get('location') || null, description: f.get('description') || null,
        program_id: f.get('program_id') ? Number(f.get('program_id')) : null,
        capacity: f.get('capacity') ? Number(f.get('capacity')) : null,
        registration_open: f.get('registration_open') === 'on',
        registration_deadline: f.get('registration_deadline') ? new Date(f.get('registration_deadline')).toISOString() : null,
      }
      if (isEdit) await apiFetch(`/api/activities/${activity.id}`, { method: 'PATCH', body })
      else await apiFetch('/api/activities', { method: 'POST', body })
      showToast(isEdit ? 'Activity updated' : 'Activity created')
      onSaved()
      onClose()
    } catch (err) { showToast(errorMessage(err)) }
    finally { setSaving(false) }
  }

  return <Modal title={isEdit ? 'Edit activity' : 'Create activity'} onClose={onClose} wide>
    <form onSubmit={save} className="grid gap-4">
      <label className="text-sm font-semibold">Title<input name="title" defaultValue={activity?.title} className="input-k mt-2" required /></label>
      <div className="grid grid-cols-2 gap-4">
        <label className="text-sm font-semibold">Type<select name="activity_type" defaultValue={activity?.activity_type || 'Social'} className="input-k mt-2">{ACTIVITY_TYPES.map(t => <option key={t}>{t}</option>)}</select></label>
        <label className="text-sm font-semibold">Date &amp; time<input name="scheduled_at" type="datetime-local" defaultValue={toLocalInput(activity?.scheduled_at)} className="input-k mt-2" required /></label>
      </div>
      <label className="text-sm font-semibold">Program (optional)
        <select name="program_id" defaultValue={activity?.program_id || ''} className="input-k mt-2">
          <option value="">No program — standalone activity</option>
          {programs.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
      </label>
      <label className="text-sm font-semibold">Location<input name="location" defaultValue={activity?.location} className="input-k mt-2" /></label>
      <label className="text-sm font-semibold">Description<textarea name="description" defaultValue={activity?.description} rows={2} className="input-k mt-2" /></label>
      <div className="grid grid-cols-2 gap-4 rounded-xl bg-kCream p-4">
        <label className="text-sm font-semibold">Capacity (optional)<input name="capacity" type="number" min="1" defaultValue={activity?.capacity} className="input-k mt-2" placeholder="Unlimited" /></label>
        <label className="text-sm font-semibold">Registration deadline<input name="registration_deadline" type="datetime-local" defaultValue={toLocalInput(activity?.registration_deadline)} className="input-k mt-2" /></label>
        <label className="col-span-2 flex items-center gap-2 text-sm font-semibold"><input name="registration_open" type="checkbox" defaultChecked={activity ? activity.registration_open : true} className="h-4 w-4" /> Registration open (volunteers can RSVP)</label>
      </div>
      <button disabled={saving} className="btn-orange mt-2 disabled:opacity-60">{saving ? 'Saving…' : isEdit ? 'Save changes' : 'Create activity'}</button>
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

  return <div>
    <div className="relative"><Search className="absolute left-3 top-3.5 text-kMuted" size={17} /><input value={q} onChange={e => setQ(e.target.value)} className="input-k pl-10" placeholder="Search a member to register..." /></div>
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

function VolunteersPanel({ activity, showToast }) {
  const [volunteers, setVolunteers] = useState([])
  const [candidates, setCandidates] = useState([])
  const [loading, setLoading] = useState(true)
  const [assigning, setAssigning] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try { setVolunteers((await apiFetch(`/api/activities/${activity.id}/volunteers`)).volunteers) }
    catch (err) { showToast(errorMessage(err)) }
    finally { setLoading(false) }
  }, [activity.id, showToast])

  useEffect(() => { load() }, [load])
  useEffect(() => { apiFetch('/api/volunteers?status=Verified').then(d => setCandidates(d.volunteers)).catch(() => {}) }, [])

  async function assign(e) {
    e.preventDefault()
    const f = new FormData(e.target)
    setAssigning(true)
    try {
      await apiFetch(`/api/activities/${activity.id}/volunteers`, { method: 'POST', body: { volunteer_id: Number(f.get('volunteer_id')), role: f.get('role') } })
      showToast('Volunteer assigned')
      e.target.reset()
      load()
    } catch (err) { showToast(errorMessage(err)) }
    finally { setAssigning(false) }
  }

  async function update(row, patch) {
    try { await apiFetch(`/api/activities/${activity.id}/volunteers/${row.id}`, { method: 'PATCH', body: patch }); load() }
    catch (err) { showToast(errorMessage(err)) }
  }

  const assignedIds = new Set(volunteers.filter(v => v.status !== 'Cancelled' && v.status !== 'Declined').map(v => v.volunteer_id))

  return <div>
    <div className="grid grid-cols-3 gap-3 text-center">
      <div className="card-k p-3"><div className="font-display text-xl font-bold text-kGreen">{activity.confirmed_volunteer_count ?? 0}</div><div className="text-xs text-kMuted">Confirmed</div></div>
      <div className="card-k p-3"><div className="font-display text-xl font-bold text-kOrange">{activity.waitlist_count ?? 0}</div><div className="text-xs text-kMuted">Waitlisted</div></div>
      <div className="card-k p-3"><div className="font-display text-xl font-bold text-kInk">{activity.capacity ?? '∞'}</div><div className="text-xs text-kMuted">Capacity</div></div>
    </div>

    <form onSubmit={assign} className="mt-5 grid grid-cols-[1fr_auto_auto] gap-2">
      <select name="volunteer_id" className="input-k" required>
        <option value="">Assign a volunteer…</option>
        {candidates.filter(c => !assignedIds.has(c.user_id)).map(c => <option key={c.user_id} value={c.user_id}>{c.name}</option>)}
      </select>
      <select name="role" defaultValue="General Volunteer" className="input-k">{VOLUNTEER_ROLES.map(r => <option key={r}>{r}</option>)}</select>
      <button disabled={assigning} className="btn-orange disabled:opacity-60"><Plus size={15} /></button>
    </form>

    {loading ? <p className="mt-4 text-sm text-kMuted">Loading…</p> : <div className="mt-5 grid gap-2">
      {volunteers.map(v => <div key={v.id} className="rounded-xl bg-kCream p-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2"><UserCheck size={14} className="text-kOrange" /><span className="text-sm font-semibold text-kInk">{v.volunteer_name}</span><span className="text-xs text-kMuted">{v.role}</span>{v.is_self_rsvp && <span className="text-[10px] font-bold uppercase text-kOrange">RSVP</span>}</div>
          <select value={v.status} onChange={e => update(v, { status: e.target.value })} className="rounded-full border-none bg-white px-2.5 py-1 text-xs font-bold text-kInk"><StatusOptions /></select>
        </div>
        <div className="mt-2 flex items-center gap-3 text-xs text-kMuted">
          {v.checked_in_at ? <span className="flex items-center gap-1 text-kGreen"><LogIn size={12} /> Checked in {fmt(v.checked_in_at)}</span> : <button onClick={() => update(v, { checked_in: true })} className="flex items-center gap-1 font-bold text-kOrange"><LogIn size={12} /> Check in</button>}
          {v.checked_in_at && (v.checked_out_at ? <span className="flex items-center gap-1 text-kGreen"><LogOut size={12} /> Checked out {fmt(v.checked_out_at)}</span> : <button onClick={() => update(v, { checked_out: true })} className="flex items-center gap-1 font-bold text-kOrange"><LogOut size={12} /> Check out</button>)}
        </div>
      </div>)}
      {volunteers.length === 0 && <p className="text-sm text-kMuted">No volunteers assigned or RSVPed yet.</p>}
    </div>}
  </div>
}

function StatusOptions() {
  return VOLUNTEER_STATUSES.map(s => <option key={s}>{s}</option>)
}

export default function ActivityManager({ showToast }) {
  const [activities, setActivities] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [typeFilter, setTypeFilter] = useState('All')
  const [statusFilter, setStatusFilter] = useState('All')
  const [selected, setSelected] = useState(null)
  const [tab, setTab] = useState('participants')
  const [formOpen, setFormOpen] = useState(null) // null | 'create' | activity-to-edit

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
      <button onClick={() => setFormOpen('create')} className="btn-green"><Plus size={16} /> Create activity</button>
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
              <div><div className="font-semibold text-kInk">{a.title}{a.program_name && <span className="ml-2 rounded-full bg-kTint px-2 py-0.5 text-[10px] font-bold text-kOrange">{a.program_name}</span>}</div><div className="text-xs text-kMuted">{a.activity_type} &middot; {fmt(a.scheduled_at)}</div></div>
              <div className="flex items-center gap-1 text-xs font-bold text-kOrange"><Users size={14} /> {a.participant_count}</div>
            </button>)}
            {activities.length === 0 && <p className="p-4 text-center text-sm text-kMuted">No activities match your filters.</p>}
          </div>}
        </div>
      </div>
      <div>
        {selected ? <div className="card-k p-6">
          <div className="flex items-start justify-between gap-3">
            <div><h2 className="font-display text-lg font-bold text-kGreen">{selected.title}</h2><p className="mt-1 text-xs text-kMuted">{selected.activity_type} &middot; {fmt(selected.scheduled_at)}{selected.location ? ` · ${selected.location}` : ''}</p></div>
            <div className="flex items-center gap-2"><StatusBadge value={selected.status} /><button onClick={() => setFormOpen(selected)} className="text-xs font-bold text-kOrange">Edit</button></div>
          </div>
          <div className="mt-4 flex gap-1 border-b border-kBorderSoft pb-2">
            <button onClick={() => setTab('participants')} className={`rounded-lg px-3 py-1.5 text-sm font-semibold ${tab === 'participants' ? 'bg-kOrange text-white' : 'text-kMuted hover:bg-kCream'}`}>Participants</button>
            <button onClick={() => setTab('volunteers')} className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-semibold ${tab === 'volunteers' ? 'bg-kOrange text-white' : 'text-kMuted hover:bg-kCream'}`}><Clock size={13} /> Volunteers</button>
          </div>
          <div className="mt-4">
            {tab === 'participants' && <ParticipantsPanel activity={selected} onChanged={load} showToast={showToast} />}
            {tab === 'volunteers' && <VolunteersPanel activity={selected} showToast={showToast} />}
          </div>
        </div> : <div className="card-k p-10 text-center text-sm text-kMuted">Select an activity to manage.</div>}
      </div>
    </div>

    {formOpen && <ActivityFormModal activity={formOpen === 'create' ? null : formOpen} onClose={() => setFormOpen(null)} onSaved={load} showToast={showToast} />}
  </Shell>
}
