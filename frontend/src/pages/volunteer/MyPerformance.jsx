import VolunteerShell from '../../components/volunteer/VolunteerShell'
import { LoadingState, ErrorState } from '../../components/admin/adminHelpers'
import { useVolunteerData } from '../../lib/VolunteerDataContext'

function StatCard({ value, label }) {
  return <div className="card-k p-6 text-center"><div className="font-display text-4xl font-bold text-kGreen">{value}</div><div className="mt-1 text-sm text-kMuted">{label}</div></div>
}

export default function MyPerformance() {
  // Shared across the portal (see VolunteerDataContext) — computed from
  // the same already-scoped data every other portal page uses, nothing
  // fabricated or estimated.
  const { visits, requests, followups, loading, error, reload } = useVolunteerData()

  if (loading) return <VolunteerShell><LoadingState label="performance" /></VolunteerShell>
  if (error) return <VolunteerShell><ErrorState message={error} onRetry={reload} /></VolunteerShell>

  const allAssignments = [...visits, ...requests]
  const completed = allAssignments.filter(x => x.status === 'Completed').length
  const cancelled = allAssignments.filter(x => x.status === 'Cancelled').length
  const pending = allAssignments.length - completed - cancelled
  const decided = completed + cancelled
  const completionRate = decided > 0 ? Math.round((completed / decided) * 100) : null

  return <VolunteerShell>
    <div><div className="eyebrow">Private to you</div><h1 className="font-display text-3xl font-bold text-kGreen">My Performance</h1></div>

    <div className="mt-7 grid gap-4 sm:grid-cols-3">
      <StatCard value={completed} label="Completed" />
      <StatCard value={pending} label="Pending" />
      <StatCard value={completionRate === null ? '—' : `${completionRate}%`} label="Completion Rate" />
    </div>
    <div className="mt-4 grid gap-4 sm:grid-cols-3">
      <StatCard value={visits.filter(x => x.status === 'Completed').length} label="Home visits completed" />
      <StatCard value={requests.filter(x => x.status === 'Completed').length} label="Assistance requests completed" />
      <StatCard value={followups.filter(x => x.status === 'Completed').length} label="Follow-ups completed" />
    </div>
    <p className="mt-6 text-xs text-kMuted">This is your own record only — no other volunteer's performance is visible here.</p>
  </VolunteerShell>
}
