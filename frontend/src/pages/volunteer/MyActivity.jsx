import { CheckCircle2 } from 'lucide-react'
import VolunteerShell from '../../components/volunteer/VolunteerShell'
import { LoadingState, ErrorState } from '../../components/admin/adminHelpers'
import { useVolunteerData } from '../../lib/VolunteerDataContext'

function fmtDay(iso) { return new Date(iso).toLocaleDateString([], { dateStyle: 'medium' }) }

export default function MyActivity() {
  // Shared across the portal (see VolunteerDataContext) — no per-page
  // fetch, so this loads instantly once the portal's first page has.
  const { visits, requests, followups, loading, error, reload } = useVolunteerData()

  if (loading) return <VolunteerShell><LoadingState label="activity" /></VolunteerShell>
  if (error) return <VolunteerShell><ErrorState message={error} onRetry={reload} /></VolunteerShell>

  const entries = [
    ...visits.filter(x => x.status === 'Completed').map(x => ({ date: x.completed_at, label: `Home visit — ${x.elderly_member_name}` })),
    ...requests.filter(x => x.status === 'Completed').map(x => ({ date: x.completed_at, label: `${x.request_type} — ${x.elderly_member_name}` })),
    ...followups.filter(x => x.status === 'Completed').map(x => ({ date: x.completed_at, label: `Follow-up completed — ${x.elderly_member_name}` })),
  ].filter(x => x.date).sort((a, b) => new Date(b.date) - new Date(a.date))

  const byDay = {}
  for (const e of entries) {
    const day = fmtDay(e.date)
    byDay[day] = byDay[day] || []
    byDay[day].push(e)
  }

  return <VolunteerShell>
    <div><div className="eyebrow">My history</div><h1 className="font-display text-3xl font-bold text-kGreen">My Activity</h1></div>

    <div className="mt-7 grid gap-6">
      {Object.entries(byDay).map(([day, items]) => <div key={day}>
        <h3 className="text-xs font-bold uppercase tracking-wide text-kMuted">{day}</h3>
        <div className="mt-3 grid gap-2">
          {items.map((e, i) => <div key={i} className="card-k flex items-center gap-3 p-4"><CheckCircle2 size={17} className="shrink-0 text-kGreen" /><span className="text-sm text-kInk">{e.label}</span></div>)}
        </div>
      </div>)}
      {entries.length === 0 && <div className="card-k p-10 text-center text-sm text-kMuted">No completed work yet — it'll show up here once you finish your first assignment.</div>}
    </div>
  </VolunteerShell>
}
