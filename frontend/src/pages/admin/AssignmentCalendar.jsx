import { useState, useEffect, useCallback } from 'react'
import { Home, HandHeart } from 'lucide-react'
import Shell from '../../components/admin/Shell'
import { LoadingState, ErrorState, errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch } from '../../lib/api'

const TYPE_ICONS = { home_visit: Home, assistance_request: HandHeart }
const TYPE_LABELS = { home_visit: 'Home Visit', assistance_request: 'Assistance' }

function groupByDay(events) {
  const groups = {}
  for (const e of events) {
    const day = e.scheduled_at.slice(0, 10)
    groups[day] = groups[day] || []
    groups[day].push(e)
  }
  return Object.entries(groups).sort(([a], [b]) => a.localeCompare(b))
}

export default function AssignmentCalendar() {
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try { setEvents((await apiFetch('/api/calendar')).events) }
    catch (err) { setError(errorMessage(err)) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const days = groupByDay(events)

  return <Shell>
    <div><div className="eyebrow">Schedule</div><h1 className="font-display text-3xl font-bold text-kGreen">Assignment calendar</h1></div>

    {loading ? <LoadingState label="calendar" /> : error ? <ErrorState message={error} onRetry={load} /> : <div className="mt-7 grid gap-4">
      {days.map(([day, dayEvents]) => <div key={day} className="card-k overflow-hidden">
        <div className="border-b border-kBorderSoft bg-kCream px-5 py-3 text-sm font-bold text-kGreen">
          {new Date(day + 'T00:00:00').toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}
        </div>
        <div className="divide-y divide-kBorderSoft">
          {dayEvents.map(e => {
            const Icon = TYPE_ICONS[e.type]
            return <div key={`${e.type}-${e.id}`} className="flex flex-wrap items-center gap-3 px-5 py-4">
              <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-kTint text-kOrange"><Icon size={18} /></div>
              <div className="flex-1">
                <div className="flex items-center gap-2"><span className="font-semibold text-kInk">{TYPE_LABELS[e.type]}</span><span className="text-xs text-kMuted">{new Date(e.scheduled_at).toLocaleTimeString([], { timeStyle: 'short' })}</span></div>
                <div className="text-sm text-kMuted">{e.elderly_member_name} &middot; {e.assigned_to || 'Unassigned'}</div>
              </div>
              <span className="text-xs font-bold uppercase tracking-wide text-kOrange">{e.status}</span>
            </div>
          })}
        </div>
      </div>)}
      {days.length === 0 && <div className="card-k p-10 text-center text-sm text-kMuted">No scheduled assignments yet.</div>}
    </div>}
  </Shell>
}
