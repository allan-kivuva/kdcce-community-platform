import { Link } from 'react-router-dom'
import { Home, HandHeart, CalendarClock, ShieldCheck, AlertTriangle } from 'lucide-react'
import VolunteerShell from '../../components/volunteer/VolunteerShell'
import { LoadingState, ErrorState } from '../../components/admin/adminHelpers'
import { getStoredUser } from '../../lib/api'
import { useVolunteerData } from '../../lib/VolunteerDataContext'

function isToday(iso) {
  if (!iso) return false
  const d = new Date(iso)
  const now = new Date()
  return d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth() && d.getDate() === now.getDate()
}
function isThisMonth(iso) {
  if (!iso) return false
  const d = new Date(iso)
  const now = new Date()
  return d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth()
}
function greeting() {
  const h = new Date().getHours()
  if (h < 12) return 'Good morning'
  if (h < 17) return 'Good afternoon'
  return 'Good evening'
}

function StatCard({ value, label }) {
  return <div className="card-k p-6 text-center"><div className="font-display text-4xl font-bold text-kGreen">{value}</div><div className="mt-1 text-sm text-kMuted">{label}</div></div>
}

export default function VolunteerDashboard({ profile }) {
  const user = getStoredUser()
  // profile comes from VolunteerPortal's own gate check (already fetched
  // to decide whether to even render this page) — no second /me call.
  // Everything else is derived from the shared VolunteerDataProvider, so
  // navigating here from another portal page is instant, not a re-fetch.
  const { visits, requests, followups, elderlyMembers: elderly, loading, error, reload } = useVolunteerData()

  if (loading) return <VolunteerShell><LoadingState label="dashboard" /></VolunteerShell>
  if (error) return <VolunteerShell><ErrorState message={error} onRetry={reload} /></VolunteerShell>
  const allAssignments = [
    ...visits.map(v => ({ ...v, kind: 'Home Visit', when: v.scheduled_at })),
    ...requests.map(r => ({ ...r, kind: 'Assistance Request', when: r.scheduled_at })),
  ]
  const openAssignments = allAssignments.filter(x => !['Completed', 'Cancelled'].includes(x.status))
  const todaysWork = openAssignments.filter(x => isToday(x.when)).sort((a, b) => new Date(a.when) - new Date(b.when))
  const completedThisMonth = allAssignments.filter(x => x.status === 'Completed' && isThisMonth(x.completed_at)).length
  const followupsDueToday = followups.filter(fu => fu.status !== 'Completed' && fu.due_date && new Date(fu.due_date).toDateString() === new Date().toDateString())
  const upcoming = openAssignments.filter(x => x.when).sort((a, b) => new Date(a.when) - new Date(b.when)).slice(0, 5)

  return <VolunteerShell>
    <div><div className="eyebrow">Welcome</div><h1 className="font-display text-3xl font-bold text-kGreen">{greeting()}, {user?.name?.split(' ')[0] || 'there'}</h1>
      <span className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-kGreen/10 px-3 py-1 text-xs font-bold text-kGreen"><ShieldCheck size={13} /> {profile.status}</span>
    </div>

    <div className="mt-7 grid gap-4 sm:grid-cols-4">
      <StatCard value={todaysWork.length} label="Today's Assignments" />
      <StatCard value={openAssignments.length} label="Pending" />
      <StatCard value={completedThisMonth} label="Completed This Month" />
      <StatCard value={elderly.length} label="Elderly Members" />
    </div>

    <div className="card-k mt-6 p-6">
      <h2 className="font-display text-lg font-bold text-kGreen">Today's Work</h2>
      {todaysWork.length === 0 ? <p className="mt-4 text-sm text-kMuted">Nothing scheduled for today.</p> : <div className="mt-4 grid gap-3">
        {todaysWork.map(x => <div key={`${x.kind}-${x.id}`} className="flex items-center justify-between gap-3 rounded-xl border border-kBorderSoft p-4">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-kTint text-kOrange">{x.kind === 'Home Visit' ? <Home size={18} /> : <HandHeart size={18} />}</div>
            <div><div className="text-sm font-semibold text-kInk">{new Date(x.when).toLocaleTimeString([], { timeStyle: 'short' })} · {x.kind}</div><div className="text-xs text-kMuted">{x.elderly_member_name}</div></div>
          </div>
          <Link to={x.kind === 'Home Visit' ? '/volunteer/home-visits' : '/volunteer/assistance'} className="text-xs font-bold text-kOrange">View Assignment</Link>
        </div>)}
      </div>}
    </div>

    {(followupsDueToday.length > 0 || openAssignments.length > 0) && <div className="card-k mt-6 border-l-4 border-kOrange p-6">
      <h2 className="flex items-center gap-2 font-display text-lg font-bold text-kGreen"><AlertTriangle size={18} className="text-kOrange" /> Attention Required</h2>
      <ul className="mt-3 grid gap-1.5 text-sm text-kInk">
        {followupsDueToday.length > 0 && <li>{followupsDueToday.length} follow-up{followupsDueToday.length > 1 ? 's' : ''} due today</li>}
        {openAssignments.length > 0 && <li>{openAssignments.length} assignment{openAssignments.length > 1 ? 's' : ''} pending</li>}
      </ul>
    </div>}

    <div className="card-k mt-6 p-6">
      <h2 className="font-display text-lg font-bold text-kGreen">Upcoming</h2>
      {upcoming.length === 0 ? <p className="mt-4 text-sm text-kMuted">Nothing scheduled yet.</p> : <div className="mt-4 grid gap-3">
        {upcoming.map(x => <div key={`up-${x.kind}-${x.id}`} className="flex items-center justify-between gap-3 rounded-xl border border-kBorderSoft p-4">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-kTint text-kOrange">{x.kind === 'Home Visit' ? <Home size={18} /> : <HandHeart size={18} />}</div>
            <div><div className="text-sm font-semibold text-kInk">{x.kind}</div><div className="text-xs text-kMuted">{x.elderly_member_name} · {new Date(x.when).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}</div></div>
          </div>
          <Link to={x.kind === 'Home Visit' ? '/volunteer/home-visits' : '/volunteer/assistance'} className="text-xs font-bold text-kOrange">View</Link>
        </div>)}
      </div>}
    </div>

    <div className="mt-6 grid gap-4 sm:grid-cols-3">
      <Link to="/volunteer/home-visits" className="card-k flex items-center gap-3 p-5 hover:border-kOrange"><CalendarClock className="text-kOrange" /><span className="font-semibold text-kInk">My Home Visits</span></Link>
      <Link to="/volunteer/assistance" className="card-k flex items-center gap-3 p-5 hover:border-kOrange"><HandHeart className="text-kOrange" /><span className="font-semibold text-kInk">Assistance Requests</span></Link>
      <Link to="/volunteer/report-concern" className="card-k flex items-center gap-3 border-kOrange/40 p-5 hover:border-kOrange"><AlertTriangle className="text-kOrange" /><span className="font-semibold text-kInk">Report a Concern</span></Link>
    </div>
  </VolunteerShell>
}
