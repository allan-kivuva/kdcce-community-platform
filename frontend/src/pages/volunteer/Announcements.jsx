import { useState, useEffect, useCallback } from 'react'
import { Megaphone } from 'lucide-react'
import VolunteerShell from '../../components/volunteer/VolunteerShell'
import StatusBadge from '../../components/admin/StatusBadge'
import { LoadingState, ErrorState, EmptyState, errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch } from '../../lib/api'

export default function Announcements() {
  const [announcements, setAnnouncements] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try { setAnnouncements((await apiFetch('/api/announcements')).announcements) }
    catch (err) { setError(errorMessage(err)) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  return <VolunteerShell>
    <div><div className="eyebrow">Communication</div><h1 className="font-display text-3xl font-bold text-kGreen">Announcements</h1></div>

    {loading ? <LoadingState label="announcements" /> : error ? <ErrorState message={error} onRetry={load} /> : <div className="mt-7 grid gap-3">
      {announcements.length === 0 && <EmptyState icon={Megaphone} title="Nothing here right now" message="Announcements from KDCCE staff will appear here." />}
      {announcements.map(a => <div key={a.id} className={`card-k p-5 ${a.priority === 'Urgent' ? 'border-l-4 border-red-500' : a.priority === 'Important' ? 'border-l-4 border-amber-500' : ''}`}>
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-display text-base font-bold text-kInk">{a.title}</span>
          {a.priority !== 'Normal' && <StatusBadge value={a.priority} />}
        </div>
        <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-kInk">{a.body}</p>
        <p className="mt-3 text-xs text-kMuted">{a.created_by} &middot; {new Date(a.created_at).toLocaleDateString([], { dateStyle: 'medium' })}</p>
      </div>)}
    </div>}
  </VolunteerShell>
}
