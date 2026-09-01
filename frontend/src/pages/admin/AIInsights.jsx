import { useState, useEffect, useCallback } from 'react'
import { LineChart, Users, ListChecks, GraduationCap, FileClock, Wallet, TrendingUp, TrendingDown, Minus, Sparkles } from 'lucide-react'
import Shell from '../../components/admin/Shell'
import { LoadingState, ErrorState, EmptyState, errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch } from '../../lib/api'

const METRIC_LABELS = {
  assistance_requests: 'Assistance requests',
  visit_completions: 'Visit completions',
  concerns: 'Concerns',
  volunteer_hours_minutes: 'Volunteer hours',
}
// Whether a rising value is the "good" direction for this metric — used
// purely for tasteful coloring, never to hide or alter the real numbers.
// null means neither direction is clearly good or bad (assistance
// requests rising could mean more need, not a problem with the program).
const METRIC_JUDGMENT = {
  assistance_requests: null,
  visit_completions: 'up-good',
  concerns: 'up-bad',
  volunteer_hours_minutes: 'up-good',
}
const REC_ICONS = { program_staffing: Users, follow_up: ListChecks, training_gap: GraduationCap, document_expiry: FileClock, budget_alert: Wallet }

function fmtMetricValue(key, value) {
  return key === 'volunteer_hours_minutes' ? `${Math.round(value / 60)}h` : String(value)
}

function trendColor(key, direction) {
  if (direction === 'flat') return 'text-kMuted'
  const judgment = METRIC_JUDGMENT[key]
  if (!judgment) return 'text-kMuted'
  const goodDirection = judgment === 'up-good' ? 'up' : 'down'
  return direction === goodDirection ? 'text-emerald-500' : 'text-red-500'
}

function TrendCard({ metricKey, trend }) {
  const color = trendColor(metricKey, trend.direction)
  const Icon = trend.direction === 'up' ? TrendingUp : trend.direction === 'down' ? TrendingDown : Minus
  return <div className="card-k p-5">
    <div className="text-xs font-bold uppercase tracking-wide text-kMuted">{METRIC_LABELS[metricKey]}</div>
    <div className="mt-2 flex items-end justify-between">
      <div className="font-display text-2xl font-bold text-kInk">{fmtMetricValue(metricKey, trend.current)}</div>
      <div className={`flex items-center gap-1 text-sm font-bold ${color}`}><Icon size={15} /> {trend.pct_change > 0 ? '+' : ''}{trend.pct_change}%</div>
    </div>
    <div className="mt-1 text-xs text-kMuted">was {fmtMetricValue(metricKey, trend.previous)} in the previous period</div>
  </div>
}

function WorkloadSection() {
  const [data, setData] = useState(null)
  const [explanation, setExplanation] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await apiFetch('/api/ai/insights/workload')
      setData(res.data)
      setExplanation(res.explanation)
    } catch (err) { setError(errorMessage(err)) }
    finally { setLoading(false) }
  }, [])
  useEffect(() => { load() }, [load])

  if (loading) return <LoadingState label="workload insights" />
  if (error) return <ErrorState message={error} onRetry={load} />

  const categories = [
    ['Overloaded volunteers', data.overloaded_volunteers, v => `${v.name} — ${v.active_count} active assignments`],
    ['Idle volunteers', data.idle_volunteers, v => v.name],
    ['High no-show volunteers', data.high_no_show_volunteers, v => `${v.name} — ${v.no_show_count} no-show(s)`],
    ['Understaffed programs', data.understaffed_programs, p => `${p.title} — short ${p.spots_short}`],
  ]
  const anyCategory = categories.some(([, rows]) => rows.length > 0)

  return <div>
    <p className="text-sm text-kMuted">{explanation}</p>
    <div className="mt-4 grid gap-4 sm:grid-cols-3">
      <div className="card-k p-5 text-center"><div className="font-display text-2xl font-bold text-kInk">{data.median_active_assignments}</div><div className="text-xs text-kMuted">Median active assignments</div></div>
      <div className="card-k p-5 text-center"><div className="font-display text-2xl font-bold text-kInk">{data.stale_concern_count}</div><div className="text-xs text-kMuted">Stale concerns</div></div>
      <div className="card-k p-5 text-center"><div className="font-display text-2xl font-bold text-kInk">{data.stale_unassigned_request_count}</div><div className="text-xs text-kMuted">Stale unassigned requests</div></div>
    </div>
    {anyCategory ? <div className="mt-5 grid gap-4 sm:grid-cols-2">
      {categories.map(([label, rows, fmt]) => rows.length > 0 && <div key={label} className="card-k p-5">
        <div className="flex items-center justify-between text-xs font-bold uppercase tracking-wide text-kMuted"><span>{label}</span><span>{rows.length}</span></div>
        <ul className="mt-2 grid gap-1.5 text-sm text-kInk">{rows.map((r, i) => <li key={i}>{fmt(r)}</li>)}</ul>
      </div>)}
    </div> : <p className="mt-4 text-sm text-kMuted">No workload issues detected.</p>}
  </div>
}

function TrendsSection() {
  const [periodDays, setPeriodDays] = useState(30)
  const [data, setData] = useState(null)
  const [explanation, setExplanation] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await apiFetch(`/api/ai/insights/trends?period_days=${periodDays}`)
      setData(res.data)
      setExplanation(res.explanation)
    } catch (err) { setError(errorMessage(err)) }
    finally { setLoading(false) }
  }, [periodDays])
  useEffect(() => { load() }, [load])

  return <div>
    <div className="flex flex-wrap items-center justify-between gap-3">
      <p className="max-w-2xl text-sm text-kMuted">{!loading && !error ? explanation : ''}</p>
      <select value={periodDays} onChange={e => setPeriodDays(Number(e.target.value))} className="input-k w-40">
        <option value={7}>Last 7 days</option><option value={30}>Last 30 days</option><option value={90}>Last 90 days</option>
      </select>
    </div>
    {loading && <div className="mt-4"><LoadingState label="trends" /></div>}
    {!loading && error && <div className="mt-4"><ErrorState message={error} onRetry={load} /></div>}
    {!loading && !error && data && <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {Object.keys(METRIC_LABELS).map(key => <TrendCard key={key} metricKey={key} trend={data[key]} />)}
    </div>}
  </div>
}

function RecommendationsSection() {
  const [items, setItems] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try { setItems((await apiFetch('/api/ai/insights/recommendations')).data.recommendations) }
    catch (err) { setError(errorMessage(err)) }
    finally { setLoading(false) }
  }, [])
  useEffect(() => { load() }, [load])

  if (loading) return <LoadingState label="recommendations" />
  if (error) return <ErrorState message={error} onRetry={load} />
  if (items.length === 0) return <EmptyState icon={Sparkles} message="No recommendations right now." />

  return <div className="grid gap-3">
    {items.map((r, i) => {
      const Icon = REC_ICONS[r.type] || Sparkles
      return <div key={i} className="card-k flex items-start gap-3 p-4">
        <div className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-kTint text-kOrange"><Icon size={17} /></div>
        <p className="text-sm text-kInk">{r.text}</p>
      </div>
    })}
  </div>
}

const TABS = [['workload', 'Workload'], ['trends', 'Trends'], ['recommendations', 'Recommendations']]

export default function AIInsights() {
  const [tab, setTab] = useState('workload')

  return <Shell>
    <div><div className="eyebrow">Smart Features</div><h1 className="flex items-center gap-2 font-display text-3xl font-bold text-kGreen"><LineChart className="text-kOrange" /> AI Insights</h1></div>

    <div className="mt-6 flex gap-1 border-b border-kBorderSoft pb-1">
      {TABS.map(([key, label]) => <button key={key} onClick={() => setTab(key)} className={`rounded-t-xl px-4 py-2 text-sm font-semibold ${tab === key ? 'bg-kGreen text-white' : 'text-kMuted hover:bg-kCream'}`}>{label}</button>)}
    </div>

    <div className="mt-6">
      {tab === 'workload' && <WorkloadSection />}
      {tab === 'trends' && <TrendsSection />}
      {tab === 'recommendations' && <RecommendationsSection />}
    </div>
  </Shell>
}
