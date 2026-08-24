import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Home, HandHeart, CalendarClock } from 'lucide-react'
import VolunteerShell from '../../components/volunteer/VolunteerShell'
import { LoadingState, ErrorState, errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch, getStoredUser } from '../../lib/api'

function isToday(iso) {
  if (!iso) return false
  const d = new Date(iso)
  const now = new Date()
  return d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth() && d.getDate() === now.getDate()
}

function StatCard({ value, label }) {
  return <div className="card-k p-6 text-center"><div className="font-display text-4xl font-bold text-kGreen">{value}</div><div className="mt-1 text-sm text-kMuted">{label}</div></div>
}

export default function VolunteerDashboard() {
  const user = getStoredUser()
  const [visits, setVisits] = useState([])
  const [requests, setRequests] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    // Both endpoints are already identity-scoped for a volunteer token —
    // this page just aggregates real data from them, no separate
    // dashboard-stats endpoint needed and no invented numbers.
    Promise.all([apiFetch('/api/home-visits'), apiFetch('/api/assistance-requests')])
      .then(([v, r]) => { setVisits(v.visits); setRequests(r.requests) })
      .catch(err => setError(errorMessage(err)))
      .finally(() => setLoading(false))
  }, [])

  const openVisits = visits.filter(v => !['Completed', 'Cancelled'].includes(v.status))
  const openRequests = requests.filter(r => !['Completed', 'Cancelled'].includes(r.status))
  const totalOpen = openVisits.length + openRequests.length
  const todayCount = [...openVisits, ...openRequests].filter(x => isToday(x.scheduled_at)).length
  const upcoming = [...openVisits.map(v => ({ ...v, kind: 'Home Visit', when: v.scheduled_at })), ...openRequests.map(r => ({ ...r, kind: 'Assistance Request', when: r.scheduled_at }))]
    .filter(x => x.when)
    .sort((a, b) => new Date(a.when) - new Date(b.when))
    .slice(0, 5)

  return <VolunteerShell>
    <div><div className="eyebrow">Welcome</div><h1 className="font-display text-3xl font-bold text-kGreen">Hi, {user?.name?.split(' ')[0] || 'there'} 👋</h1></div>

    {loading ? <LoadingState label="dashboard" /> : error ? <ErrorState message={error} onRetry={() => window.location.reload()} /> : <>
      <div className="mt-7 grid gap-4 sm:grid-cols-3">
        <StatCard value={totalOpen} label="Open assignments" />
        <StatCard value={todayCount} label="Today" />
        <StatCard value={upcoming.length} label="Upcoming" />
      </div>

      <div className="card-k mt-6 p-6">
        <h2 className="font-display text-lg font-bold text-kGreen">Upcoming</h2>
        {upcoming.length === 0 ? <p className="mt-4 text-sm text-kMuted">Nothing scheduled yet.</p> : <div className="mt-4 grid gap-3">
          {upcoming.map(x => <div key={`${x.kind}-${x.id}`} className="flex items-center justify-between gap-3 rounded-xl border border-kBorderSoft p-4">
            <div className="flex items-center gap-3">
              <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-kTint text-kOrange">{x.kind === 'Home Visit' ? <Home size={18} /> : <HandHeart size={18} />}</div>
              <div><div className="text-sm font-semibold text-kInk">{x.kind}</div><div className="text-xs text-kMuted">{x.elderly_member_name} · {new Date(x.when).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}</div></div>
            </div>
            <Link to={x.kind === 'Home Visit' ? '/volunteer/home-visits' : '/volunteer/assistance'} className="text-xs font-bold text-kOrange">View</Link>
          </div>)}
        </div>}
      </div>

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <Link to="/volunteer/home-visits" className="card-k flex items-center gap-3 p-5 hover:border-kOrange"><CalendarClock className="text-kOrange" /><span className="font-semibold text-kInk">My Home Visits</span></Link>
        <Link to="/volunteer/assistance" className="card-k flex items-center gap-3 p-5 hover:border-kOrange"><HandHeart className="text-kOrange" /><span className="font-semibold text-kInk">Assistance Requests</span></Link>
      </div>
    </>}
  </VolunteerShell>
}
