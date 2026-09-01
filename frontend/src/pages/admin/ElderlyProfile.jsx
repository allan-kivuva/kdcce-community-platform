import { useState, useEffect, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, ClipboardCheck, Heart, Pill, Utensils, Home, HandHeart, ShieldAlert, AlertTriangle, Camera, Sparkles } from 'lucide-react'
import Shell from '../../components/admin/Shell'
import StatusBadge from '../../components/admin/StatusBadge'
import { LoadingState, ErrorState, errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch } from '../../lib/api'

const TABS = [
  ['overview', 'Overview'], ['timeline', 'Timeline'], ['health', 'Health'], ['medication', 'Medication'],
  ['attendance', 'Attendance'], ['meal', 'Meals'], ['home_visit', 'Visits'], ['assistance', 'Assistance'],
  ['incident', 'Incidents'], ['followups', 'Follow-ups'],
]

const TYPE_ICONS = { attendance: ClipboardCheck, health: Heart, medication: Pill, meal: Utensils, home_visit: Home, assistance: HandHeart, incident: ShieldAlert }

function fmtDay(iso) { return new Date(iso).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' }) }
function fmtTime(iso) { return new Date(iso).toLocaleTimeString([], { timeStyle: 'short' }) }

function TimelineEntry({ event }) {
  const Icon = TYPE_ICONS[event.type] || ClipboardCheck
  const d = event.details
  return <div className="flex gap-3 border-b border-kBorderSoft py-4 last:border-0">
    <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-kTint text-kOrange"><Icon size={17} /></div>
    <div className="flex-1">
      <div className="flex flex-wrap items-center gap-2"><span className="font-semibold text-kInk">{event.title}</span><span className="text-xs text-kMuted">{fmtDay(event.timestamp)} &middot; {fmtTime(event.timestamp)}</span></div>
      <div className="mt-1 grid gap-0.5 text-sm text-kMuted">
        {d.assigned_to && <div>Assigned: {d.assigned_to}</div>}
        {d.status && <div>Status: {d.status}</div>}
        {d.severity && <div>Severity: {d.severity}</div>}
        {(d.observations || d.description || d.reason) && <div>{d.observations || d.description || d.reason}</div>}
        {d.medication_name && <div>{d.medication_name}{d.notes ? ` — ${d.notes}` : ''}</div>}
        {d.mood && <div>Mood: {d.mood}{d.temperature_celsius != null ? ` · ${d.temperature_celsius}°C` : ''}</div>}
        {d.follow_up_required && <div className="font-semibold text-kOrange">Follow-up required</div>}
        {d.has_photo && <div className="flex items-center gap-1 text-kOrange"><Camera size={13} /> Photo attached</div>}
      </div>
    </div>
  </div>
}

function TimelineSummaryBox({ memberId }) {
  const [days, setDays] = useState(30)
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function generate() {
    setLoading(true)
    setError('')
    setSummary(null)
    try {
      const res = await apiFetch(`/api/ai/elderly/${memberId}/timeline-summary`, { method: 'POST', body: { days } })
      setSummary(res.summary)
    } catch (err) { setError(errorMessage(err)) }
    finally { setLoading(false) }
  }

  return <div className="mb-4 rounded-xl border border-kBorderSoft bg-kCream p-4">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div className="flex items-center gap-2 text-sm font-bold text-kGreen"><Sparkles size={15} /> AI-generated summary</div>
      <div className="flex items-center gap-2">
        <select value={days} onChange={e => setDays(Number(e.target.value))} className="input-k w-32 py-1.5 text-xs">
          <option value={7}>Last 7 days</option><option value={30}>Last 30 days</option><option value={90}>Last 90 days</option>
        </select>
        <button onClick={generate} disabled={loading} className="btn-orange px-3 py-1.5 text-xs disabled:opacity-60">{loading ? 'Summarizing…' : 'Summarize'}</button>
      </div>
    </div>
    {error && <p className="mt-2 text-xs font-semibold text-red-500">{error}</p>}
    {summary && <p className="mt-3 text-sm leading-6 text-kInk">{summary}</p>}
  </div>
}

export default function ElderlyProfile() {
  const { id } = useParams()
  const [member, setMember] = useState(null)
  const [timeline, setTimeline] = useState([])
  const [followups, setFollowups] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [tab, setTab] = useState('overview')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [timelineRes, followupsRes] = await Promise.all([
        apiFetch(`/api/elderly/${id}/timeline?per_page=100`),
        apiFetch(`/api/followups?elderly_member_id=${id}`),
      ])
      setMember(timelineRes.member)
      setTimeline(timelineRes.timeline)
      setFollowups(followupsRes.followups)
    } catch (err) { setError(errorMessage(err)) }
    finally { setLoading(false) }
  }, [id])

  useEffect(() => { load() }, [load])

  if (loading) return <Shell><LoadingState label="profile" /></Shell>
  if (error) return <Shell><ErrorState message={error} onRetry={load} /></Shell>

  const filtered = tab === 'overview' || tab === 'timeline' || tab === 'followups' ? timeline : timeline.filter(e => e.type === tab)
  const openFollowups = followups.filter(f => f.status !== 'Completed').length

  return <Shell>
    <Link to="/admin/elderly" className="flex items-center gap-1 text-sm font-semibold text-kOrange"><ArrowLeft size={15} /> Back to elderly members</Link>

    <div className="mt-4 flex flex-wrap items-center justify-between gap-4">
      <div>
        <h1 className="font-display text-3xl font-bold text-kGreen">{member.full_name}</h1>
        <p className="text-sm text-kMuted">{member.member_id}{member.opa_name ? ` · ${member.opa_name}` : ''}</p>
      </div>
      <div className="flex items-center gap-3">
        <StatusBadge value={member.status} />
        {openFollowups > 0 && <span className="flex items-center gap-1 rounded-full bg-red-50 px-3 py-1 text-xs font-bold text-red-700"><AlertTriangle size={13} /> {openFollowups} open follow-up{openFollowups > 1 ? 's' : ''}</span>}
      </div>
    </div>

    <div className="mt-6 flex gap-1 overflow-x-auto border-b border-kBorderSoft pb-1">
      {TABS.map(([key, label]) => <button key={key} onClick={() => setTab(key)} className={`shrink-0 rounded-t-xl px-4 py-2 text-sm font-semibold ${tab === key ? 'bg-kGreen text-white' : 'text-kMuted hover:bg-kCream'}`}>{label}</button>)}
    </div>

    {tab === 'overview' && <div className="mt-6 grid gap-6 lg:grid-cols-2">
      <div className="card-k p-6">
        <h2 className="font-display text-lg font-bold text-kGreen">Details</h2>
        <dl className="mt-4 grid gap-3 text-sm">
          <div className="flex justify-between"><dt className="text-kMuted">Gender</dt><dd className="font-semibold text-kInk">{member.gender}</dd></div>
          <div className="flex justify-between"><dt className="text-kMuted">Date of birth</dt><dd className="font-semibold text-kInk">{member.date_of_birth || '—'}</dd></div>
          <div className="flex justify-between"><dt className="text-kMuted">Location</dt><dd className="font-semibold text-kInk">{member.location || '—'}</dd></div>
          <div className="flex justify-between"><dt className="text-kMuted">Registered</dt><dd className="font-semibold text-kInk">{member.registration_date}</dd></div>
        </dl>
        <h3 className="mt-6 text-xs font-bold uppercase tracking-wide text-kMuted">Emergency contact</h3>
        <p className="mt-2 text-sm text-kInk">{member.emergency_contact_name || 'Not on file'}{member.emergency_contact_phone ? ` · ${member.emergency_contact_phone}` : ''}{member.emergency_contact_relationship ? ` (${member.emergency_contact_relationship})` : ''}</p>
      </div>
      <div className="card-k p-6">
        <h2 className="font-display text-lg font-bold text-kGreen">Health &amp; vulnerability</h2>
        <div className="mt-4 grid gap-3 text-sm">
          <div><span className="text-xs font-bold uppercase text-kMuted">Vulnerability notes</span><p className="mt-1 text-kInk">{member.vulnerability_notes || '—'}</p></div>
          <div><span className="text-xs font-bold uppercase text-kMuted">Health notes</span><p className="mt-1 text-kInk">{member.health_notes || '—'}</p></div>
          <div><span className="text-xs font-bold uppercase text-kMuted">Allergies</span><p className="mt-1 text-kInk">{member.allergies || '—'}</p></div>
          <div><span className="text-xs font-bold uppercase text-kMuted">Dietary requirements</span><p className="mt-1 text-kInk">{member.dietary_requirements || '—'}</p></div>
        </div>
      </div>
      <div className="card-k p-6 lg:col-span-2">
        <h2 className="font-display text-lg font-bold text-kGreen">Recent activity</h2>
        <div className="mt-2">{timeline.slice(0, 5).map(e => <TimelineEntry key={`${e.type}-${e.timestamp}`} event={e} />)}
          {timeline.length === 0 && <p className="py-4 text-sm text-kMuted">No recorded activity yet.</p>}</div>
      </div>
    </div>}

    {tab === 'followups' ? <div className="card-k mt-6 p-6">
      {followups.map(f => <div key={f.id} className="flex items-center justify-between gap-3 border-b border-kBorderSoft py-4 last:border-0">
        <div><div className="font-semibold text-kInk">{f.reason}</div><div className="text-xs text-kMuted">{f.assigned_to || 'Unassigned'}{f.due_date ? ` · Due ${f.due_date}` : ''}</div></div>
        <span className="text-xs font-bold uppercase tracking-wide text-kOrange">{f.status}</span>
      </div>)}
      {followups.length === 0 && <p className="py-4 text-sm text-kMuted">No follow-ups for this member.</p>}
    </div> : tab !== 'overview' && <div className="card-k mt-6 p-6">
      {tab === 'timeline' && <TimelineSummaryBox memberId={id} />}
      {filtered.map(e => <TimelineEntry key={`${e.type}-${e.timestamp}`} event={e} />)}
      {filtered.length === 0 && <p className="py-4 text-sm text-kMuted">No records in this category yet.</p>}
    </div>}
  </Shell>
}
