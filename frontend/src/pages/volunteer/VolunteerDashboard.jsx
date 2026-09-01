import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Award, Clock, GraduationCap, Home, HandHeart, CalendarClock, ShieldCheck, AlertTriangle, Megaphone, MessageSquare, Sparkles, Target } from 'lucide-react'
import VolunteerShell from '../../components/volunteer/VolunteerShell'
import { LoadingState, ErrorState, errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch, getStoredUser } from '../../lib/api'
import { useVolunteerData } from '../../lib/VolunteerDataContext'

function fmtMinutes(minutes) {
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  if (h === 0) return `${m}m`
  if (m === 0) return `${h}h`
  return `${h}h ${m}m`
}

function ImpactSection() {
  const [impact, setImpact] = useState(null)
  useEffect(() => {
    Promise.all([apiFetch('/api/volunteers/me/hours'), apiFetch('/api/volunteers/me/achievements')])
      .then(([h, a]) => setImpact({ hours: h.hours, achievementCount: a.achievements.earned.length, nextMilestone: a.achievements.upcoming[0] || null }))
      .catch(() => {}) // impact is a nice-to-have on the dashboard, never blocks the rest of the page
  }, [])
  if (!impact) return null
  return <div className="card-k mt-6 p-6">
    <h2 className="font-display text-lg font-bold text-kGreen">My Impact</h2>
    <div className="mt-4 grid gap-4 sm:grid-cols-4">
      <div className="flex items-center gap-3"><div className="grid h-10 w-10 place-items-center rounded-xl bg-kTint text-kOrange"><Clock size={18} /></div><div><div className="font-display text-xl font-bold text-kInk">{fmtMinutes(impact.hours.minutes_this_month)}</div><div className="text-xs text-kMuted">This month</div></div></div>
      <div className="flex items-center gap-3"><div className="grid h-10 w-10 place-items-center rounded-xl bg-kTint text-kOrange"><Clock size={18} /></div><div><div className="font-display text-xl font-bold text-kInk">{fmtMinutes(impact.hours.minutes_lifetime)}</div><div className="text-xs text-kMuted">Lifetime hours</div></div></div>
      <div className="flex items-center gap-3"><div className="grid h-10 w-10 place-items-center rounded-xl bg-kTint text-kOrange"><Award size={18} /></div><div><div className="font-display text-xl font-bold text-kInk">{impact.achievementCount}</div><div className="text-xs text-kMuted">Achievements</div></div></div>
      <div className="flex items-center gap-3"><div className="grid h-10 w-10 place-items-center rounded-xl bg-kTint text-kOrange"><GraduationCap size={18} /></div><div className="min-w-0"><div className="truncate font-display text-sm font-bold text-kInk">{impact.nextMilestone ? impact.nextMilestone.name : 'All caught up'}</div><div className="text-xs text-kMuted">{impact.nextMilestone ? `${impact.nextMilestone.current_value}/${impact.nextMilestone.threshold_value}` : 'Next milestone'}</div></div></div>
    </div>
  </div>
}

function BriefingSection() {
  const [facts, setFacts] = useState(null)
  useEffect(() => {
    apiFetch('/api/ai/volunteer/briefing').then(res => setFacts(res.facts)).catch(() => {}) // nice-to-have, never blocks the dashboard
  }, [])
  if (!facts) return null
  const t = facts.today

  return <div className="card-k mt-6 p-6">
    <h2 className="flex items-center gap-2 font-display text-lg font-bold text-kGreen"><Sparkles size={18} /> Today at a glance</h2>
    <div className="mt-4 grid gap-4 sm:grid-cols-3">
      <div className="flex items-center gap-3"><div className="grid h-10 w-10 place-items-center rounded-xl bg-kTint text-kOrange"><CalendarClock size={18} /></div><div><div className="font-display text-xl font-bold text-kInk">{t.assignment_count}</div><div className="text-xs text-kMuted">Assignments today</div></div></div>
      <div className="flex items-center gap-3"><div className="grid h-10 w-10 place-items-center rounded-xl bg-kTint text-kOrange"><MessageSquare size={18} /></div><div><div className="font-display text-xl font-bold text-kInk">{t.unread_messages}</div><div className="text-xs text-kMuted">Unread messages</div></div></div>
      <div className="flex items-center gap-3"><div className="grid h-10 w-10 place-items-center rounded-xl bg-kTint text-kOrange"><GraduationCap size={18} /></div><div><div className="font-display text-xl font-bold text-kInk">{t.training_outstanding}</div><div className="text-xs text-kMuted">Training outstanding</div></div></div>
    </div>
    {facts.next_milestone && <div className="mt-4 flex items-center gap-2 rounded-xl bg-kOrange/10 px-4 py-3 text-sm font-semibold text-kOrange"><Target size={15} /> {facts.next_milestone.remaining} more toward "{facts.next_milestone.name}"</div>}
  </div>
}

function CommunicationSection() {
  const [data, setData] = useState(null)
  useEffect(() => {
    Promise.all([apiFetch('/api/messages/conversations'), apiFetch('/api/announcements')])
      .then(([c, a]) => setData({
        conversations: [...c.conversations].sort((x, y) => new Date(y.updated_at) - new Date(x.updated_at)).slice(0, 3),
        unreadCount: c.conversations.reduce((s, x) => s + x.unread_count, 0),
        announcements: a.announcements.slice(0, 2),
      }))
      .catch(() => {}) // a nice-to-have preview — a failed fetch just leaves the section hidden
  }, [])
  if (!data) return null
  if (data.conversations.length === 0 && data.announcements.length === 0) return null

  return <div className="card-k mt-6 p-6">
    <div className="flex items-center justify-between">
      <h2 className="flex items-center gap-2 font-display text-lg font-bold text-kGreen"><MessageSquare size={18} /> Messages {data.unreadCount > 0 && <span className="rounded-full bg-kOrange px-2 py-0.5 text-xs font-bold text-white">{data.unreadCount} unread</span>}</h2>
      <Link to="/volunteer/messages" className="text-sm font-semibold text-kOrange">View all messages</Link>
    </div>
    {data.conversations.length === 0 ? <p className="mt-3 text-sm text-kMuted">No conversations yet.</p> : <div className="mt-4 grid gap-2">
      {data.conversations.map(c => <Link key={c.id} to="/volunteer/messages" className="flex items-center justify-between gap-3 rounded-xl border border-kBorderSoft p-3 hover:border-kOrange">
        <div className="min-w-0"><div className="truncate text-sm font-semibold text-kInk">{c.other_user.name}</div><div className="truncate text-xs text-kMuted">{c.last_message?.body}</div></div>
        {c.unread_count > 0 && <span className="shrink-0 h-2 w-2 rounded-full bg-kOrange" />}
      </Link>)}
    </div>}

    {data.announcements.length > 0 && <div className="mt-5 border-t border-kBorderSoft pt-4">
      <h3 className="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-kMuted"><Megaphone size={13} /> Announcements</h3>
      <div className="mt-2 grid gap-2">
        {data.announcements.map(a => <div key={a.id} className={`rounded-xl p-3 text-sm ${a.priority === 'Urgent' ? 'bg-red-500/10' : 'bg-kCream'}`}>
          <div className="font-semibold text-kInk">{a.title}</div>
          <div className="mt-0.5 truncate text-xs text-kMuted">{a.body}</div>
        </div>)}
      </div>
    </div>}
  </div>
}

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

    <ImpactSection />
    <BriefingSection />
    <CommunicationSection />

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
