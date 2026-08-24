import { useState, useEffect, useCallback } from 'react'
import { AlertTriangle, AlertCircle, AreaChart, Calendar } from 'lucide-react'
import Shell from '../../components/admin/Shell'
import { LoadingState, ErrorState, errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch } from '../../lib/api'

function StatTile({ label, value, tone = 'default' }) {
  const toneClass = tone === 'warn' ? 'text-kOrange' : tone === 'danger' ? 'text-red-600' : 'text-kGreen'
  return <div className="card-k p-5"><div className="text-sm text-kMuted">{label}</div><div className={`mt-2 font-display text-3xl font-bold ${toneClass}`}>{value}</div></div>
}

function Section({ title, children }) {
  return <div className="mt-8"><h2 className="font-display text-xl font-bold text-kGreen">{title}</h2><div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{children}</div></div>
}

function TrendChart({ title, series, days }) {
  if (!series || series.length === 0) return null
  const max = Math.max(...series.map(d => d.count), 1)
  const step = days > 7 ? 2 : 1
  return <div className="card-k mt-5 p-6">
    <div className="flex items-center gap-3"><div className="grid h-10 w-10 place-items-center rounded-xl bg-kTint text-kOrange"><AreaChart size={18} /></div><h3 className="font-display text-lg font-bold text-kGreen">{title}</h3></div>
    <div className="mt-6 flex h-32 items-end justify-between gap-1">
      {series.map((d, i) => <div key={d.date} className="flex flex-1 flex-col items-center gap-2"><div className="w-full rounded-t-lg bg-kOrange/75" style={{ height: `${Math.max((d.count / max) * 100, 2)}%` }} title={`${d.date}: ${d.count}`} />{i % step === 0 && <span className="text-[9px] text-kMuted">{d.date.slice(5)}</span>}</div>)}
    </div>
  </div>
}

export default function AnalyticsManager() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try { setData((await apiFetch('/api/analytics/dashboard')).dashboard) }
    catch (err) { setError(errorMessage(err)) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  return <Shell>
    <div><div className="eyebrow">Management intelligence</div><h1 className="font-display text-3xl font-bold text-kGreen">Analytics dashboard</h1></div>

    {loading ? <LoadingState label="dashboard" /> : error ? <ErrorState message={error} onRetry={load} /> : <>
      {data.incidents.open > 0 && <div className="mt-6 flex items-center gap-2 rounded-xl border-l-4 border-l-red-500 bg-red-50 px-5 py-3 text-sm font-semibold text-red-700 dark:bg-red-500/10"><AlertCircle size={16} /> {data.incidents.open} open incident{data.incidents.open > 1 ? 's' : ''} need attention</div>}
      {data.feeding_resources.low_stock_items > 0 && <div className="mt-3 flex items-center gap-2 rounded-xl border-l-4 border-l-kOrange bg-kTint px-5 py-3 text-sm font-semibold text-kOrange"><AlertTriangle size={16} /> {data.feeding_resources.low_stock_items} item{data.feeding_resources.low_stock_items > 1 ? 's' : ''} at or below minimum stock</div>}

      <Section title="Elderly Care">
        <StatTile label="Total elderly members" value={data.elderly_care.total_elderly_members} />
        <StatTile label="New registrations (30d)" value={data.elderly_care.new_registrations_30d} />
        <StatTile label="Today's attendance" value={data.elderly_care.today_attendance} />
        <StatTile label="Health follow-ups required" value={data.elderly_care.follow_ups_required} tone={data.elderly_care.follow_ups_required > 0 ? 'warn' : 'default'} />
      </Section>
      <TrendChart title="Attendance — last 7 days" series={data.elderly_care.attendance_trend_7d} days={7} />

      <Section title="Home &amp; Community Support">
        <StatTile label="Home visits pending" value={data.home_community.home_visits_pending} />
        <StatTile label="Home visits active" value={data.home_community.home_visits_active} />
        <StatTile label="Assistance pending" value={data.home_community.assistance_pending} />
        <StatTile label="Active volunteers" value={data.home_community.active_volunteers} />
      </Section>

      <Section title="Health">
        <StatTile label="Health checks (30d)" value={data.health.health_checks_30d} />
        <StatTile label="Follow-ups required" value={data.health.follow_ups_required} tone={data.health.follow_ups_required > 0 ? 'warn' : 'default'} />
        <StatTile label="Medication activity (7d)" value={data.health.medication_administrations_7d} />
        <StatTile label="Clinic visits" value="Not tracked yet" />
      </Section>

      <Section title="Feeding &amp; Resources">
        <StatTile label="Meals served (7d)" value={data.feeding_resources.meals_served_7d} />
        <StatTile label="Low stock items" value={data.feeding_resources.low_stock_items} tone={data.feeding_resources.low_stock_items > 0 ? 'warn' : 'default'} />
        <StatTile label="Inventory movements (7d)" value={data.feeding_resources.inventory_movements_7d} />
        <StatTile label="Donations (30d)" value={data.feeding_resources.donations_30d} />
      </Section>
      <div className="grid gap-5 xl:grid-cols-2">
        <TrendChart title="Meals served — last 7 days" series={data.feeding_resources.meals_trend_7d} days={7} />
        <TrendChart title="Donations — last 14 days" series={data.feeding_resources.donations_trend_14d} days={14} />
      </div>

      <Section title="Activities">
        <StatTile label="Upcoming activities" value={data.activities.upcoming_count} />
        <StatTile label="Attended (30d)" value={data.activities.attended_30d} />
      </Section>
      {data.activities.upcoming.length > 0 && <div className="card-k mt-5 overflow-hidden">
        <div className="border-b border-kBorderSoft px-5 py-3 text-sm font-bold text-kGreen">Next up</div>
        {data.activities.upcoming.map(a => <div key={a.id} className="flex items-center gap-3 border-b border-kBorderSoft px-5 py-3 text-sm last:border-0"><Calendar size={15} className="text-kOrange" /><span className="font-semibold text-kInk">{a.title}</span><span className="text-kMuted">{a.activity_type} &middot; {new Date(a.scheduled_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}</span></div>)}
      </div>}

      <Section title="Incidents">
        <StatTile label="Open" value={data.incidents.open} tone={data.incidents.open > 0 ? 'danger' : 'default'} />
        <StatTile label="Follow-up required" value={data.incidents.follow_up_required} tone={data.incidents.follow_up_required > 0 ? 'warn' : 'default'} />
      </Section>
      {data.incidents.recent.length > 0 && <div className="card-k mt-5 overflow-hidden">
        <div className="border-b border-kBorderSoft px-5 py-3 text-sm font-bold text-kGreen">Recent incidents</div>
        {data.incidents.recent.map(i => <div key={i.id} className="flex items-center justify-between border-b border-kBorderSoft px-5 py-3 text-sm last:border-0"><span className="font-semibold text-kInk">{i.elderly_member_name}</span><span className="text-kMuted">{i.incident_type}</span><span className="text-xs font-bold uppercase text-kOrange">{i.status}</span></div>)}
      </div>}
    </>}
  </Shell>
}
