import { useState, useEffect, useCallback } from 'react'
import { Award, Clock, GraduationCap, Heart, Home, ShieldCheck, Star, Trophy } from 'lucide-react'
import VolunteerShell from '../../components/volunteer/VolunteerShell'
import { LoadingState, ErrorState, errorMessage, timeAgo } from '../../components/admin/adminHelpers'
import { apiFetch } from '../../lib/api'

const ACHIEVEMENT_ICONS = { Home, HandHeart: Heart, Clock, GraduationCap, Star, Award, Trophy, ShieldCheck }

function fmtMinutes(minutes) {
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  if (h === 0) return `${m}m`
  if (m === 0) return `${h}h`
  return `${h}h ${m}m`
}

function StatCard({ value, label }) {
  return <div className="card-k p-6 text-center"><div className="font-display text-4xl font-bold text-kGreen">{value}</div><div className="mt-1 text-sm text-kMuted">{label}</div></div>
}

function AchievementBadge({ entry, earned }) {
  const name = earned ? entry.achievement.name : entry.name
  const icon = earned ? entry.achievement.icon : entry.icon
  const Icon = ACHIEVEMENT_ICONS[icon] || Award
  return <div className={`flex flex-col items-center gap-2 rounded-2xl border p-4 text-center ${earned ? 'border-kOrange/30 bg-kTint' : 'border-kBorderSoft opacity-60'}`}>
    <div className={`grid h-12 w-12 place-items-center rounded-full ${earned ? 'bg-kOrange text-white' : 'bg-kBorderSoft text-kMuted'}`}><Icon size={22} /></div>
    <div className="text-xs font-bold text-kInk">{name}</div>
    {!earned && entry.threshold_value != null && <div className="text-[10px] text-kMuted">{entry.threshold_type === 'service_minutes' ? `${fmtMinutes(entry.current_value)}/${fmtMinutes(entry.threshold_value)}` : `${entry.current_value}/${entry.threshold_value}`}</div>}
    {earned && <div className="text-[10px] text-kMuted">{new Date(entry.awarded_at).toLocaleDateString([], { dateStyle: 'medium' })}</div>}
  </div>
}

function MonthlyBars({ data, formatValue }) {
  const max = Math.max(...data.map(d => d.value), 1)
  return <div className="mt-4 flex h-28 items-end justify-between gap-2">
    {data.map(d => <div key={d.label} className="flex flex-1 flex-col items-center gap-2" title={`${d.label}: ${formatValue(d.value)}`}>
      <div className="w-full rounded-t-md bg-kOrange/70" style={{ height: `${Math.max((d.value / max) * 100, d.value > 0 ? 4 : 1)}%` }} />
      <span className="text-[10px] text-kMuted">{d.label}</span>
    </div>)}
  </div>
}

export default function MyPerformance() {
  const [hours, setHours] = useState(null)
  const [performance, setPerformance] = useState(null)
  const [achievements, setAchievements] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [h, p, a] = await Promise.all([
        apiFetch('/api/volunteers/me/hours'),
        apiFetch('/api/volunteers/me/performance'),
        apiFetch('/api/volunteers/me/achievements'),
      ])
      setHours(h.hours)
      setPerformance(p.performance)
      setAchievements(a.achievements)
    } catch (err) { setError(errorMessage(err)) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  if (loading) return <VolunteerShell><LoadingState label="performance" /></VolunteerShell>
  if (error) return <VolunteerShell><ErrorState message={error} onRetry={load} /></VolunteerShell>

  // Last 6 months, built from recent_entries (already-fetched real data —
  // no separate monthly-aggregate endpoint needed for a 6-bar chart).
  const monthLabels = Array.from({ length: 6 }, (_, i) => {
    const d = new Date()
    d.setMonth(d.getMonth() - (5 - i))
    return { key: d.toISOString().slice(0, 7), label: d.toLocaleDateString([], { month: 'short' }) }
  })
  const hoursByMonth = monthLabels.map(m => ({
    label: m.label,
    value: hours.recent_entries.filter(e => e.date.slice(0, 7) === m.key).reduce((s, e) => s + e.minutes, 0),
  }))

  const manualRecognition = achievements.earned.filter(e => e.source === 'manual')
  const milestones = achievements.earned.filter(e => e.source === 'automatic')

  return <VolunteerShell>
    <div><div className="eyebrow">Private to you</div><h1 className="font-display text-3xl font-bold text-kGreen">My Performance</h1></div>

    <h2 className="mt-8 text-xs font-bold uppercase tracking-wide text-kMuted">Service hours</h2>
    <div className="mt-3 grid gap-4 sm:grid-cols-4">
      <StatCard value={fmtMinutes(hours.minutes_today)} label="Today" />
      <StatCard value={fmtMinutes(hours.minutes_this_week)} label="This Week" />
      <StatCard value={fmtMinutes(hours.minutes_this_month)} label="This Month" />
      <StatCard value={fmtMinutes(hours.minutes_lifetime)} label="Lifetime" />
    </div>

    <div className="card-k mt-4 p-6">
      <h3 className="font-display text-lg font-bold text-kGreen">Hours by month</h3>
      <MonthlyBars data={hoursByMonth} formatValue={fmtMinutes} />
    </div>

    <h2 className="mt-8 text-xs font-bold uppercase tracking-wide text-kMuted">Assignments</h2>
    <div className="mt-3 grid gap-4 sm:grid-cols-3">
      <StatCard value={performance.total_completed_assignments} label="Completed" />
      <StatCard value={performance.pending_assignments} label="Pending" />
      <StatCard value={performance.completion_rate === null ? '—' : `${performance.completion_rate}%`} label="Completion Rate" />
    </div>
    <div className="mt-4 grid gap-4 sm:grid-cols-2">
      <StatCard value={performance.completed_home_visits} label="Home visits completed" />
      <StatCard value={performance.completed_assistance_requests} label="Assistance requests completed" />
    </div>

    <h2 className="mt-8 text-xs font-bold uppercase tracking-wide text-kMuted">Achievements</h2>
    {milestones.length === 0 && achievements.upcoming.length === 0 ? <p className="mt-3 text-sm text-kMuted">Nothing to show yet.</p> : <>
      {milestones.length > 0 && <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {milestones.map(e => <AchievementBadge key={e.achievement.code} entry={e} earned />)}
      </div>}
      {achievements.upcoming.length > 0 && <>
        <div className="mt-5 text-xs font-semibold text-kMuted">Upcoming milestones</div>
        <div className="mt-2 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {achievements.upcoming.slice(0, 4).map(e => <AchievementBadge key={e.code} entry={e} earned={false} />)}
        </div>
      </>}
    </>}

    {manualRecognition.length > 0 && <>
      <h2 className="mt-8 text-xs font-bold uppercase tracking-wide text-kMuted">Recognition</h2>
      <div className="mt-3 grid gap-3">
        {manualRecognition.map(e => <div key={e.achievement.code} className="card-k flex items-center gap-4 p-5">
          <div className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-kOrange text-white"><Trophy size={20} /></div>
          <div className="flex-1">
            <div className="font-display text-base font-bold text-kInk">{e.achievement.name}</div>
            {e.notes && <div className="mt-0.5 text-sm text-kMuted">{e.notes}</div>}
            <div className="mt-0.5 text-xs text-kMuted">Awarded by {e.awarded_by || 'KDCCE staff'} &middot; {timeAgo(e.awarded_at)}</div>
          </div>
        </div>)}
      </div>
    </>}

    <p className="mt-8 text-xs text-kMuted">This is your own record only — no other volunteer's performance is visible here.</p>
  </VolunteerShell>
}
