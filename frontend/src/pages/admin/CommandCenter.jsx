import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  AlertCircle, AlertTriangle, CalendarDays, CheckCircle2, ChevronLeft, ChevronRight, ClipboardCheck, Heart, HeartHandshake, Home,
  MapPin, MessageCircle, ShieldAlert, Sparkles, TrendingUp, UserPlus,
} from 'lucide-react'
import Shell from '../../components/admin/Shell'
import Modal from '../../components/admin/Modal'
import StatCard from '../../components/admin/StatCard'
import StatusBadge from '../../components/admin/StatusBadge'
import { LoadingState, ErrorState, errorMessage, timeAgo } from '../../components/admin/adminHelpers'
import { apiFetch } from '../../lib/api'
import { useApiResource } from '../../lib/useApiResource'

const INCIDENT_STATUSES = ['Open', 'Under Review', 'Resolved', 'Closed']
const INCIDENT_SEVERITIES = ['Low', 'Medium', 'High', 'Critical']

/** Buckets `items` into one count/value per day for the last `days` days
 * (today inclusive), keyed off `dateField`. valueFn defaults to "count
 * one per item"; pass e.g. d => Number(d.amount) to sum a field instead.
 * Purely a client-side aggregate over already-fetched real records — no
 * fabricated numbers, just a different view of the same data. */
function dailySeries(items, dateField, days, valueFn = () => 1) {
  const today = new Date()
  const buckets = []
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(today)
    d.setDate(d.getDate() - i)
    buckets.push({ key: d.toISOString().slice(0, 10), value: 0 })
  }
  const index = Object.fromEntries(buckets.map((b, i) => [b.key, i]))
  for (const item of items) {
    const raw = item[dateField]
    if (!raw) continue
    const key = raw.slice(0, 10)
    if (key in index) buckets[index[key]].value += valueFn(item)
  }
  return buckets
}

function pctChange(curr, prev) {
  if (!prev) return null
  return Math.round(((curr - prev) / prev) * 1000) / 10
}

function sumSeries(series) { return series.reduce((s, b) => s + b.value, 0) }

function isoDay(offsetDays = 0) {
  const d = new Date()
  d.setDate(d.getDate() + offsetDays)
  return d.toISOString().slice(0, 10)
}

function fmtTime(iso) { return iso ? new Date(iso).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }) : '—' }
function fmtDate(iso) { return iso ? new Date(iso).toLocaleDateString([], { dateStyle: 'medium' }) : '—' }
function initials(name) { return (name || '?').split(' ').map(p => p[0]).slice(0, 2).join('').toUpperCase() }

function useDashboardData() {
  const [analytics, setAnalytics] = useState(null)
  const [incidents, setIncidents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [dash, inc] = await Promise.all([apiFetch('/api/analytics/dashboard'), apiFetch('/api/incidents')])
      setAnalytics(dash.dashboard)
      setIncidents(inc.incidents)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])
  return { analytics, incidents, loading, error, reload: load, setIncidents }
}

function KpiRow({ analytics, incidents, homeVisits, donationsMonth, donationTrendPct }) {
  const todayCount = homeVisits.filter(v => v.scheduled_at?.slice(0, 10) === isoDay(0)).length
  const yesterdayCount = homeVisits.filter(v => v.scheduled_at?.slice(0, 10) === isoDay(-1)).length
  const visitsSeries = dailySeries(homeVisits, 'scheduled_at', 7).map(b => b.value)
  const openConcerns = incidents.filter(i => i.status === 'Open').length
  const criticalConcerns = incidents.filter(i => i.status === 'Open' && i.severity === 'Critical').length

  return <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
    <StatCard icon={HeartHandshake} tone="blue" label="Active Volunteers" value={analytics.home_community.active_volunteers} />
    <StatCard icon={ClipboardCheck} tone="purple" label="Pending Requests"
      value={analytics.home_community.home_visits_pending + analytics.home_community.assistance_pending}
      subtitle={`${analytics.home_community.home_visits_pending} visits · ${analytics.home_community.assistance_pending} assistance`} />
    <StatCard icon={Home} tone="cyan" label="Today's Visits" value={todayCount}
      trendPct={pctChange(todayCount, yesterdayCount)} trendLabel="vs yesterday" sparkline={visitsSeries} />
    <StatCard icon={ShieldAlert} tone="red" label="Open Concerns" value={openConcerns}
      subtitle={criticalConcerns > 0 ? `${criticalConcerns} critical` : 'None critical'} />
    <StatCard icon={Heart} tone="green" label="Donations (MTD)" value={`KES ${donationsMonth.total.toLocaleString()}`}
      trendPct={donationTrendPct} trendLabel="vs previous 7 days" sparkline={donationsMonth.series} />
  </div>
}

function RecentActivity({ incidents, homeVisits, volunteers, donations }) {
  const items = [
    ...incidents.slice(0, 5).map(i => ({
      key: `inc-${i.id}`, icon: ShieldAlert, tone: 'text-red-500 bg-red-500/10', time: i.occurred_at,
      title: 'Concern reported', who: i.elderly_member_name || 'General', status: i.status,
    })),
    ...donations.slice(0, 5).map(d => ({
      key: `don-${d.id}`, icon: Heart, tone: 'text-emerald-500 bg-emerald-500/10', time: d.created_at,
      title: 'Donation received', who: d.donor_name, amount: d.amount != null ? `+KES ${Number(d.amount).toLocaleString()}` : null,
    })),
    ...volunteers.slice(0, 5).map(v => ({
      key: `vol-${v.id}`, icon: UserPlus, tone: 'text-blue-500 bg-blue-500/10', time: v.created_at,
      title: 'Volunteer application', who: v.name, status: v.status,
    })),
    ...homeVisits.filter(v => v.status === 'Completed' && v.completed_at).slice(0, 5).map(v => ({
      key: `visit-${v.id}`, icon: CheckCircle2, tone: 'text-cyan-500 bg-cyan-500/10', time: v.completed_at,
      title: 'Home visit completed', who: v.elderly_member_name, status: 'Completed',
    })),
  ].sort((a, b) => new Date(b.time) - new Date(a.time)).slice(0, 7)

  return <div className="card-k p-6">
    <div className="flex items-center justify-between"><h2 className="font-display text-lg font-bold text-kInk">Recent Activity</h2><Link to="/admin/analytics" className="text-sm font-semibold text-kOrange">View all</Link></div>
    <div className="mt-4 grid gap-1">
      {items.length === 0 && <p className="py-8 text-center text-sm text-kMuted">No recent activity yet.</p>}
      {items.map(it => <div key={it.key} className="flex items-center gap-3 border-b border-kBorderSoft py-3 last:border-0">
        <div className={`grid h-9 w-9 shrink-0 place-items-center rounded-full ${it.tone}`}><it.icon size={16} /></div>
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-semibold text-kInk">{it.title}</div>
          <div className="truncate text-xs text-kMuted">{it.who} &middot; {timeAgo(it.time)}</div>
        </div>
        {it.amount ? <span className="shrink-0 text-sm font-bold text-emerald-500">{it.amount}</span> : it.status ? <StatusBadge value={it.status} /> : null}
      </div>)}
    </div>
  </div>
}

function AssignmentsBoard({ homeVisits }) {
  const board = homeVisits
    .filter(v => v.assigned_to && ['Assigned', 'Accepted', 'Scheduled', 'Started', 'In Progress'].includes(v.status))
    .sort((a, b) => new Date(a.scheduled_at || a.created_at) - new Date(b.scheduled_at || b.created_at))
    .slice(0, 6)

  return <div className="card-k p-6">
    <div className="flex items-center justify-between"><h2 className="font-display text-lg font-bold text-kInk">Assignments Board</h2><Link to="/admin/home-visits" className="text-sm font-semibold text-kOrange">View all</Link></div>
    <div className="mt-4 grid gap-1">
      {board.length === 0 && <p className="py-8 text-center text-sm text-kMuted">No active assignments right now.</p>}
      {board.map(v => <Link key={v.id} to="/admin/home-visits" className="flex items-center gap-3 rounded-xl border-b border-kBorderSoft px-1 py-3 transition last:border-0 hover:bg-kTint">
        <div className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-blue-500/10 text-xs font-bold text-blue-500">{initials(v.assigned_to)}</div>
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-semibold text-kInk">{v.assigned_to}</div>
          <div className="truncate text-xs text-kMuted">Home visit &middot; {v.elderly_member_name}{v.scheduled_at ? ` · ${fmtDate(v.scheduled_at)} ${fmtTime(v.scheduled_at)}` : ''}</div>
        </div>
        <StatusBadge value={v.status} />
      </Link>)}
    </div>
  </div>
}

function UpcomingVisits({ homeVisits }) {
  const [offset, setOffset] = useState(0)
  const dayKey = isoDay(offset)
  const dayVisits = homeVisits
    .filter(v => v.scheduled_at?.slice(0, 10) === dayKey)
    .sort((a, b) => new Date(a.scheduled_at) - new Date(b.scheduled_at))
  const label = offset === 0 ? 'Today' : new Date(dayKey).toLocaleDateString([], { month: 'long', day: 'numeric', year: 'numeric' })

  return <div className="card-k p-6">
    <div className="flex items-center justify-between">
      <h2 className="font-display text-lg font-bold text-kInk">Upcoming Visits</h2>
      <Link to="/admin/calendar" className="flex items-center gap-1 text-sm font-semibold text-kOrange"><CalendarDays size={14} /> View calendar</Link>
    </div>
    <div className="mt-4 flex items-center justify-between rounded-xl bg-kTint px-3 py-2">
      <button onClick={() => setOffset(o => o - 1)} className="grid h-7 w-7 place-items-center rounded-lg text-kMuted hover:bg-kBorderSoft"><ChevronLeft size={16} /></button>
      <span className="text-sm font-bold text-kInk">{label}</span>
      <button onClick={() => setOffset(o => o + 1)} className="grid h-7 w-7 place-items-center rounded-lg text-kMuted hover:bg-kBorderSoft"><ChevronRight size={16} /></button>
    </div>
    <div className="mt-4 grid gap-1">
      {dayVisits.length === 0 && <p className="py-8 text-center text-sm text-kMuted">No visits scheduled.</p>}
      {dayVisits.map(v => <div key={v.id} className="flex items-start gap-3 border-b border-kBorderSoft py-3 last:border-0">
        <div className="w-16 shrink-0 text-xs font-bold text-kOrange">{fmtTime(v.scheduled_at)}</div>
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-semibold text-kInk">{v.elderly_member_name}</div>
          <div className="mt-0.5 flex items-center gap-1 text-xs text-kMuted"><MapPin size={11} />{v.assigned_to || 'Unassigned'}</div>
        </div>
        <StatusBadge value={v.status} />
      </div>)}
    </div>
  </div>
}

function ConcernEditModal({ incident, onClose, onSaved, showToast }) {
  const [saving, setSaving] = useState(false)
  async function save(e) {
    e.preventDefault()
    const f = new FormData(e.target)
    setSaving(true)
    try {
      await apiFetch(`/api/incidents/${incident.id}`, { method: 'PATCH', body: { status: f.get('status'), severity: f.get('severity'), resolution_notes: f.get('resolution_notes') || null } })
      showToast('Concern updated')
      onSaved()
      onClose()
    } catch (err) { showToast(errorMessage(err)) }
    finally { setSaving(false) }
  }
  return <Modal title={`${incident.elderly_member_name || 'General concern'} — ${incident.incident_type}`} onClose={onClose}>
    <div className="mb-4 rounded-xl bg-kCream p-3 text-sm text-kInk">{incident.description}</div>
    <form onSubmit={save} className="grid gap-4">
      <div className="grid grid-cols-2 gap-4">
        <label className="text-sm font-semibold">Status<select name="status" defaultValue={incident.status} className="input-k mt-2">{INCIDENT_STATUSES.map(s => <option key={s}>{s}</option>)}</select></label>
        <label className="text-sm font-semibold">Priority<select name="severity" defaultValue={incident.severity} className="input-k mt-2">{INCIDENT_SEVERITIES.map(s => <option key={s}>{s}</option>)}</select></label>
      </div>
      <label className="text-sm font-semibold">Resolution notes<textarea name="resolution_notes" defaultValue={incident.resolution_notes} rows={3} className="input-k mt-2" /></label>
      <button disabled={saving} className="btn-orange mt-2 disabled:opacity-60">{saving ? 'Saving…' : 'Save changes'}</button>
    </form>
  </Modal>
}

function UrgentConcerns({ incidents, onUpdated, showToast }) {
  const [editing, setEditing] = useState(null)
  const rows = incidents.slice(0, 8)

  return <div className="card-k overflow-hidden">
    <div className="flex items-center justify-between p-6 pb-0"><h2 className="font-display text-lg font-bold text-kInk">Urgent Concerns</h2><Link to="/admin/incidents" className="text-sm font-semibold text-kOrange">View all</Link></div>
    <div className="mt-4 overflow-x-auto"><table className="w-full min-w-[720px] text-left text-sm">
      <thead className="border-b border-kBorderSoft text-xs uppercase tracking-wider text-kMuted"><tr>
        <th className="px-6 py-3">Concern</th><th className="py-3">Reported By</th><th className="py-3">Priority</th><th className="py-3">Status</th><th className="py-3">Reported On</th>
      </tr></thead>
      <tbody>
        {rows.map(i => <tr key={i.id} onClick={() => setEditing(i)} className="cursor-pointer border-b border-kBorderSoft transition last:border-0 hover:bg-kTint">
          <td className="px-6 py-4"><div className="font-semibold text-kInk">{i.incident_type}</div><div className="max-w-xs truncate text-xs text-kMuted">{i.elderly_member_name || 'General'} &middot; {i.description}</div></td>
          <td className="py-4 text-kMuted">{i.reported_by}</td>
          <td className="py-4"><StatusBadge value={i.severity} /></td>
          <td className="py-4"><StatusBadge value={i.status} /></td>
          <td className="py-4 text-kMuted">{fmtDate(i.occurred_at)}</td>
        </tr>)}
        {rows.length === 0 && <tr><td colSpan={5} className="px-6 py-10 text-center text-sm text-kMuted">No concerns reported.</td></tr>}
      </tbody>
    </table></div>
    <div className="h-2" />
    {editing && <ConcernEditModal incident={editing} onClose={() => setEditing(null)} onSaved={onUpdated} showToast={showToast} />}
  </div>
}

function DonationOverview({ series, total, donorCount, trendPct }) {
  const max = Math.max(...series.map(b => b.value), 1)
  return <div className="card-k p-6">
    <div className="flex items-center justify-between">
      <div><h2 className="font-display text-lg font-bold text-kInk">Donation Overview</h2><p className="text-xs text-kMuted">This month</p></div>
      <Link to="/admin/donations" className="flex items-center gap-1 text-sm font-semibold text-kOrange"><TrendingUp size={14} /> View report</Link>
    </div>
    <div className="mt-4 flex flex-wrap items-end gap-8">
      <div><div className="text-xs font-semibold uppercase tracking-wide text-kMuted">Total Donations</div><div className="mt-1 font-display text-3xl font-bold text-kInk">KES {total.toLocaleString()}</div></div>
      <div><div className="text-xs font-semibold uppercase tracking-wide text-kMuted">Donors</div><div className="mt-1 font-display text-2xl font-bold text-kInk">{donorCount}</div></div>
      {typeof trendPct === 'number' && <div className={`flex items-center gap-1 text-sm font-bold ${trendPct >= 0 ? 'text-emerald-500' : 'text-red-500'}`}><TrendingUp size={15} /> {trendPct >= 0 ? '+' : ''}{trendPct}% vs prev. 7 days</div>}
    </div>
    <div className="mt-6 flex h-28 items-end justify-between gap-1.5">
      {series.map(b => <div key={b.key} className="flex flex-1 flex-col items-center gap-2" title={`${b.key}: KES ${b.value.toLocaleString()}`}>
        <div className="w-full rounded-t-md bg-emerald-500/70" style={{ height: `${Math.max((b.value / max) * 100, b.value > 0 ? 4 : 1)}%` }} />
        <span className="text-[9px] text-kMuted">{b.key.slice(5)}</span>
      </div>)}
    </div>
  </div>
}

function CommunicationWidget() {
  const [data, setData] = useState(null)
  useEffect(() => {
    Promise.all([
      apiFetch('/api/messages/unread-count'),
      apiFetch('/api/messages/unresolved'),
      apiFetch('/api/messages/conversations'),
      apiFetch('/api/announcements?all=true'),
    ]).then(([unread, unresolved, conversations, announcements]) => {
      const now = new Date()
      const active = announcements.announcements.filter(a => a.active && (!a.publish_at || new Date(a.publish_at) <= now) && (!a.expires_at || new Date(a.expires_at) > now))
      setData({
        unread: unread.unread_count,
        needsReply: unresolved.unresolved.length,
        recent: [...conversations.conversations].sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at)).slice(0, 4),
        activeAnnouncements: active.length,
      })
    }).catch(() => {}) // a communication-widget fetch failure shouldn't block the rest of the dashboard
  }, [])
  if (!data) return null

  return <div className="card-k p-6">
    <div className="flex items-center justify-between"><h2 className="font-display text-lg font-bold text-kInk">Communication</h2><Link to="/admin/messages" className="text-sm font-semibold text-kOrange">Open inbox</Link></div>
    <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
      <Link to="/admin/messages" className="rounded-xl bg-kTint p-3 text-center hover:opacity-80"><div className="font-display text-xl font-bold text-kOrange">{data.unread}</div><div className="text-xs text-kMuted">Unread</div></Link>
      <Link to="/admin/messages" className="rounded-xl bg-kTint p-3 text-center hover:opacity-80"><div className="font-display text-xl font-bold text-kOrange">{data.needsReply}</div><div className="text-xs text-kMuted">Needs Reply</div></Link>
      <div className="rounded-xl bg-kTint p-3 text-center"><div className="font-display text-xl font-bold text-kInk">{data.recent.length}</div><div className="text-xs text-kMuted">Conversations</div></div>
      <Link to="/admin/announcements" className="rounded-xl bg-kTint p-3 text-center hover:opacity-80"><div className="font-display text-xl font-bold text-kInk">{data.activeAnnouncements}</div><div className="text-xs text-kMuted">Active Announcements</div></Link>
    </div>
    <div className="mt-4 grid gap-1">
      {data.recent.length === 0 && <p className="py-4 text-center text-sm text-kMuted">No conversations yet.</p>}
      {data.recent.map(c => <div key={c.id} className="flex items-center gap-3 border-b border-kBorderSoft py-2.5 last:border-0">
        <div className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-blue-500/10 text-blue-500">{c.unread_count > 0 ? <AlertCircle size={14} /> : <MessageCircle size={14} />}</div>
        <div className="min-w-0 flex-1"><div className="truncate text-sm font-semibold text-kInk">{c.other_user.name}</div><div className="truncate text-xs text-kMuted">{c.last_message?.body}</div></div>
      </div>)}
    </div>
  </div>
}

function FinanceWidget() {
  const [data, setData] = useState(null)
  useEffect(() => {
    Promise.all([apiFetch('/api/reports/campaigns'), apiFetch('/api/reports/budgets'), apiFetch('/api/reports/donors')])
      .then(([campaigns, budgets, donors]) => {
        setData({
          activeCampaigns: campaigns.report.campaigns.filter(c => c.status === 'Active').length,
          budgetRemaining: budgets.report.total_allocated - budgets.report.total_spent,
          overBudgetCount: budgets.report.over_budget_programs.length,
          donorCount: donors.report.donor_count,
        })
      })
      .catch(() => {}) // a small dashboard widget failing to load shouldn't block the rest of the page
  }, [])
  if (!data) return null

  return <div className="card-k p-6">
    <div className="flex items-center justify-between"><h2 className="font-display text-lg font-bold text-kInk">Finance</h2><Link to="/admin/finance" className="text-sm font-semibold text-kOrange">Open finance dashboard</Link></div>
    <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
      <Link to="/admin/campaigns" className="rounded-xl bg-kTint p-3 text-center hover:opacity-80"><div className="font-display text-xl font-bold text-kOrange">{data.activeCampaigns}</div><div className="text-xs text-kMuted">Active Campaigns</div></Link>
      <Link to="/admin/budgets" className="rounded-xl bg-kTint p-3 text-center hover:opacity-80"><div className="font-display text-xl font-bold text-kInk">KES {Number(data.budgetRemaining).toLocaleString()}</div><div className="text-xs text-kMuted">Budget Remaining</div></Link>
      <Link to="/admin/budgets" className="rounded-xl bg-kTint p-3 text-center hover:opacity-80"><div className={`font-display text-xl font-bold ${data.overBudgetCount > 0 ? 'text-red-500' : 'text-kInk'}`}>{data.overBudgetCount}</div><div className="text-xs text-kMuted">Over Budget</div></Link>
      <Link to="/admin/donors" className="rounded-xl bg-kTint p-3 text-center hover:opacity-80"><div className="font-display text-xl font-bold text-kInk">{data.donorCount}</div><div className="text-xs text-kMuted">Total Donors</div></Link>
    </div>
  </div>
}

function AIAssistantWidget() {
  const [data, setData] = useState(null)
  useEffect(() => {
    apiFetch('/api/ai/admin/briefing').then(res => {
      const n = res.facts.needs_attention
      const needsAttentionCount = Object.values(n).reduce((sum, list) => sum + list.length, 0)
      setData({ today: res.facts.today, needsAttentionCount })
    }).catch(() => {}) // a small dashboard widget failing to load shouldn't block the rest of the page
  }, [])
  if (!data) return null

  return <div className="card-k p-6">
    <div className="flex items-center justify-between"><h2 className="flex items-center gap-2 font-display text-lg font-bold text-kInk"><Sparkles size={17} className="text-kOrange" /> AI Assistant</h2><Link to="/admin/ai-assistant" className="text-sm font-semibold text-kOrange">Open assistant</Link></div>
    <div className="mt-4 grid grid-cols-3 gap-3">
      <div className="rounded-xl bg-kTint p-3 text-center"><div className="font-display text-xl font-bold text-kOrange">{data.today.visits_scheduled}</div><div className="text-xs text-kMuted">Visits Today</div></div>
      <div className="rounded-xl bg-kTint p-3 text-center"><div className="font-display text-xl font-bold text-kInk">{data.today.unassigned_requests}</div><div className="text-xs text-kMuted">Unassigned</div></div>
      <div className="rounded-xl bg-kTint p-3 text-center"><div className={`font-display text-xl font-bold ${data.today.high_priority_concerns_open > 0 ? 'text-red-500' : 'text-kInk'}`}>{data.today.high_priority_concerns_open}</div><div className="text-xs text-kMuted">High-Priority</div></div>
    </div>
    {data.needsAttentionCount > 0 && <div className="mt-4 flex items-center gap-2 rounded-xl bg-amber-500/10 px-3 py-2 text-xs font-semibold text-amber-600"><AlertTriangle size={13} /> {data.needsAttentionCount} item(s) need attention</div>}
  </div>
}

export default function CommandCenter({ showToast }) {
  const { analytics, incidents, loading: dashLoading, error: dashError, reload: reloadDash } = useDashboardData()
  const homeVisitsApi = useApiResource('/api/home-visits', { listKey: 'visits', itemKey: 'visit' })
  const volunteersApi = useApiResource('/api/volunteers', { listKey: 'volunteers', itemKey: 'volunteer' })
  const donationsApi = useApiResource('/api/donations', { listKey: 'donations', itemKey: 'donation' })

  const loading = dashLoading || homeVisitsApi.loading || volunteersApi.loading || donationsApi.loading
  const error = dashError || homeVisitsApi.error || donationsApi.error || volunteersApi.error

  function retryAll() { reloadDash(); homeVisitsApi.reload(); volunteersApi.reload(); donationsApi.reload() }

  return <Shell>
    <div><div className="eyebrow">Overview</div><h1 className="font-display text-3xl font-bold text-kInk">Command Center</h1></div>

    {loading ? <LoadingState label="dashboard" /> : error ? <ErrorState message={error} onRetry={retryAll} /> : (() => {
      const completedDonations = donationsApi.items.filter(d => d.amount != null && (d.status === 'Paid' || d.status === 'Received'))
      const thisMonthKey = new Date().toISOString().slice(0, 7)
      const monthDonations = completedDonations.filter(d => d.created_at.slice(0, 7) === thisMonthKey)
      const donationSeries = dailySeries(completedDonations, 'created_at', 14, d => Number(d.amount))
      const last7 = sumSeries(donationSeries.slice(7))
      const prev7 = sumSeries(donationSeries.slice(0, 7))
      const recentVolunteers = [...volunteersApi.items].sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
      const recentDonations = [...donationsApi.items].sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
      const sortedIncidents = [...incidents].sort((a, b) => new Date(b.occurred_at) - new Date(a.occurred_at))

      return <>
        <div className="mt-7"><KpiRow
          analytics={analytics} incidents={incidents} homeVisits={homeVisitsApi.items}
          donationsMonth={{ total: monthDonations.reduce((s, d) => s + Number(d.amount), 0), series: donationSeries.slice(7).map(b => b.value) }}
          donationTrendPct={pctChange(last7, prev7)}
        /></div>

        <div className="mt-6 grid gap-6 xl:grid-cols-3">
          <RecentActivity incidents={sortedIncidents} homeVisits={homeVisitsApi.items} volunteers={recentVolunteers} donations={recentDonations} />
          <AssignmentsBoard homeVisits={homeVisitsApi.items} />
          <UpcomingVisits homeVisits={homeVisitsApi.items} />
        </div>

        <div className="mt-6 grid gap-6 xl:grid-cols-3"><CommunicationWidget /><FinanceWidget /><AIAssistantWidget /></div>

        <div className="mt-6 grid gap-6 xl:grid-cols-[1.3fr_1fr]">
          <UrgentConcerns incidents={sortedIncidents} onUpdated={reloadDash} showToast={showToast} />
          <DonationOverview series={donationSeries} total={monthDonations.reduce((s, d) => s + Number(d.amount), 0)} donorCount={new Set(monthDonations.map(d => d.donor_email || d.donor_name)).size} trendPct={pctChange(last7, prev7)} />
        </div>
      </>
    })()}
  </Shell>
}
