import { useState, useEffect, useCallback } from 'react'
import { Calendar, CheckCircle2, Clock, FileText, MapPin, Users, XCircle } from 'lucide-react'
import VolunteerShell from '../../components/volunteer/VolunteerShell'
import Modal from '../../components/admin/Modal'
import StatusBadge from '../../components/admin/StatusBadge'
import { LoadingState, ErrorState, EmptyState, errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch, downloadFile } from '../../lib/api'

const FILTERS = ['Upcoming', 'My RSVPs', 'My Assignments', 'Past']

function fmt(iso) { return new Date(iso).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }) }

function ActivityDetailModal({ activity, myAssignment, onClose, onChanged, showToast }) {
  const [resources, setResources] = useState([])
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    apiFetch(`/api/resources?activity_id=${activity.id}`).then(d => setResources(d.resources)).catch(() => {})
  }, [activity.id])

  async function doRsvp() {
    setBusy(true)
    try { await apiFetch(`/api/activities/${activity.id}/rsvp`, { method: 'POST' }); showToast('RSVP sent'); onChanged() }
    catch (err) { showToast(errorMessage(err)) }
    finally { setBusy(false) }
  }

  async function cancelRsvp() {
    if (!window.confirm('Cancel your RSVP for this event?')) return
    setBusy(true)
    try { await apiFetch(`/api/activities/${activity.id}/rsvp`, { method: 'DELETE' }); showToast('RSVP cancelled'); onChanged() }
    catch (err) { showToast(errorMessage(err)) }
    finally { setBusy(false) }
  }

  async function respond(status) {
    setBusy(true)
    try { await apiFetch(`/api/activities/${activity.id}/volunteers/${myAssignment.id}`, { method: 'PATCH', body: { status } }); showToast(`Assignment ${status.toLowerCase()}`); onChanged() }
    catch (err) { showToast(errorMessage(err)) }
    finally { setBusy(false) }
  }

  const full = activity.capacity != null && activity.spots_remaining === 0

  return <Modal title="Event details" onClose={onClose}>
    <div className="grid gap-4">
      <div>
        <div className="flex items-center gap-2"><span className="font-display text-lg font-bold text-kGreen">{activity.title}</span><StatusBadge value={activity.status} /></div>
        {activity.program_name && <div className="mt-1 text-xs font-bold text-kOrange">{activity.program_name}</div>}
      </div>
      {activity.description && <p className="text-sm text-kInk">{activity.description}</p>}
      <div className="grid gap-1.5 text-sm text-kMuted">
        <div className="flex items-center gap-2"><Clock size={14} /> {fmt(activity.scheduled_at)}</div>
        {activity.location && <div className="flex items-center gap-2"><MapPin size={14} /> {activity.location}</div>}
        {activity.capacity != null && <div className="flex items-center gap-2"><Users size={14} /> {activity.confirmed_volunteer_count}/{activity.capacity} confirmed{activity.waitlist_count > 0 ? ` · ${activity.waitlist_count} waitlisted` : ''}</div>}
      </div>

      {myAssignment && !myAssignment.is_self_rsvp && <div className="rounded-xl bg-kTint p-4">
        <div className="text-sm font-bold text-kInk">Your staffing assignment</div>
        <div className="mt-1 text-sm text-kMuted">Role: {myAssignment.role} &middot; Status: <StatusBadge value={myAssignment.status} /></div>
        {myAssignment.status === 'Assigned' && <div className="mt-3 flex gap-2">
          <button disabled={busy} onClick={() => respond('Confirmed')} className="flex items-center gap-1.5 rounded-xl bg-kGreen px-3 py-2 text-xs font-bold text-white disabled:opacity-60"><CheckCircle2 size={13} /> Confirm</button>
          <button disabled={busy} onClick={() => respond('Declined')} className="flex items-center gap-1.5 rounded-xl border border-kBorder px-3 py-2 text-xs font-bold text-kMuted disabled:opacity-60"><XCircle size={13} /> Decline</button>
        </div>}
      </div>}

      {myAssignment && myAssignment.is_self_rsvp && myAssignment.status !== 'Cancelled' && myAssignment.status !== 'Declined' && <div className="rounded-xl bg-kTint p-4">
        <div className="text-sm font-bold text-kInk">Your RSVP: <StatusBadge value={myAssignment.status} /></div>
        <button disabled={busy} onClick={cancelRsvp} className="mt-3 rounded-xl border border-kBorder px-3 py-2 text-xs font-bold text-kMuted disabled:opacity-60">Cancel RSVP</button>
      </div>}

      {!myAssignment && activity.registration_open && <button disabled={busy} onClick={doRsvp} className="btn-orange w-fit disabled:opacity-60">{busy ? 'Sending…' : full ? 'Join waitlist' : 'RSVP to this event'}</button>}
      {!myAssignment && !activity.registration_open && <p className="text-sm text-kMuted">Registration is closed for this event.</p>}

      {resources.length > 0 && <div>
        <div className="text-xs font-bold uppercase tracking-wide text-kMuted">Resources</div>
        <div className="mt-2 grid gap-1.5">
          {resources.map(r => <button key={r.id} onClick={() => downloadFile(`/api/resources/${r.id}/file`, r.title)} className="flex w-full items-center gap-2 rounded-xl bg-kCream px-3 py-2 text-left text-sm text-kInk hover:bg-kTint"><FileText size={14} className="text-kOrange" /> {r.title}</button>)}
        </div>
      </div>}
    </div>
  </Modal>
}

export default function VolunteerPrograms({ showToast }) {
  const [activities, setActivities] = useState([])
  const [assignments, setAssignments] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [filter, setFilter] = useState('Upcoming')
  const [selected, setSelected] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [a, m] = await Promise.all([apiFetch('/api/activities'), apiFetch('/api/activities/me/assignments')])
      setActivities(a.activities)
      setAssignments(m.assignments)
    } catch (err) { setError(errorMessage(err)) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const assignmentByActivity = Object.fromEntries(assignments.map(a => [a.activity_id, a]))
  const now = new Date()

  let items = activities
  if (filter === 'Upcoming') items = activities.filter(a => new Date(a.scheduled_at) > now && a.status !== 'Cancelled')
  else if (filter === 'Past') items = activities.filter(a => new Date(a.scheduled_at) <= now)
  else if (filter === 'My RSVPs') items = activities.filter(a => assignmentByActivity[a.id]?.is_self_rsvp && !['Cancelled', 'Declined'].includes(assignmentByActivity[a.id]?.status))
  else if (filter === 'My Assignments') items = activities.filter(a => assignmentByActivity[a.id] && !assignmentByActivity[a.id].is_self_rsvp)
  items = [...items].sort((a, b) => new Date(a.scheduled_at) - new Date(b.scheduled_at))

  return <VolunteerShell>
    <div><div className="eyebrow">Get involved</div><h1 className="font-display text-3xl font-bold text-kGreen">Programs &amp; Events</h1></div>
    <p className="mt-2 text-sm text-kMuted">Browse upcoming activities, RSVP, and see your assigned shifts.</p>

    <div className="mt-5 flex gap-2 overflow-x-auto">
      {FILTERS.map(f => <button key={f} onClick={() => setFilter(f)} className={`shrink-0 rounded-full px-4 py-1.5 text-xs font-bold ${filter === f ? 'bg-kOrange text-white' : 'bg-kCream text-kMuted'}`}>{f}</button>)}
    </div>

    <div className="mt-5">
      {loading && <LoadingState label="activities" />}
      {!loading && error && <ErrorState message={error} onRetry={load} />}
      {!loading && !error && items.length === 0 && <EmptyState icon={Calendar} title="Nothing here" message="No activities match this filter right now." />}
      {!loading && !error && items.length > 0 && <div className="grid gap-3">
        {items.map(a => { const my = assignmentByActivity[a.id]; return <button key={a.id} onClick={() => setSelected(a)} className="card-k flex w-full items-center justify-between gap-3 p-5 text-left hover:border-kOrange">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2"><span className="font-semibold text-kInk">{a.title}</span>{a.program_name && <span className="rounded-full bg-kTint px-2 py-0.5 text-[10px] font-bold text-kOrange">{a.program_name}</span>}</div>
            <div className="mt-1 text-xs text-kMuted">{fmt(a.scheduled_at)}{a.location ? ` · ${a.location}` : ''}{a.capacity != null ? ` · ${a.spots_remaining ?? 0} spots left` : ''}</div>
          </div>
          {my ? <StatusBadge value={my.status} /> : <span className="shrink-0 text-xs font-bold text-kOrange">View</span>}
        </button> })}
      </div>}
    </div>

    {selected && <ActivityDetailModal activity={selected} myAssignment={assignmentByActivity[selected.id]} onClose={() => setSelected(null)} onChanged={() => { load(); setSelected(null) }} showToast={showToast} />}
  </VolunteerShell>
}
