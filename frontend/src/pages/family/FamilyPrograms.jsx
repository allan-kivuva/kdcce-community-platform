import { useCallback, useEffect, useState } from 'react'
import { Calendar } from 'lucide-react'
import FamilyShell from '../../components/family/FamilyShell'
import StatusBadge from '../../components/admin/StatusBadge'
import { LoadingState, ErrorState, EmptyState, errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch } from '../../lib/api'

export default function FamilyPrograms() {
  const [members, setMembers] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [activities, setActivities] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await apiFetch('/api/family/members')
      setMembers(res.members)
      if (res.members.length > 0) setSelectedId(res.members[0].id)
    } catch (err) { setError(errorMessage(err)) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    if (!selectedId) return
    apiFetch(`/api/family/members/${selectedId}/programs`).then(d => setActivities(d.activities)).catch(err => setError(errorMessage(err)))
  }, [selectedId])

  if (loading) return <FamilyShell><LoadingState label="programs" /></FamilyShell>
  if (error) return <FamilyShell><ErrorState message={error} onRetry={load} /></FamilyShell>
  if (members.length === 0) return <FamilyShell><EmptyState icon={Calendar} title="No linked family members yet" /></FamilyShell>

  return <FamilyShell>
    <div><div className="eyebrow">Getting involved</div><h1 className="font-display text-3xl font-bold text-kGreen">Programs &amp; Events</h1></div>
    {members.length > 1 && (
      <div className="mt-4 flex flex-wrap gap-2">
        {members.map(m => <button key={m.id} onClick={() => setActivities(null) || setSelectedId(m.id)} className={`rounded-full px-4 py-2 text-sm font-bold ${selectedId === m.id ? 'bg-kGreen text-white' : 'bg-kTint text-kInk'}`}>{m.full_name}</button>)}
      </div>
    )}
    <div className="mt-6 grid gap-3">
      {!activities ? <LoadingState label="programs" /> : <>
        {activities.map(a => <div key={a.id} className="card-k flex items-center justify-between gap-4 p-5">
          <div>
            <div className="font-semibold text-kInk">{a.title}</div>
            <div className="mt-1 text-xs text-kMuted">{a.activity_type}{a.location ? ` · ${a.location}` : ''}{a.scheduled_at ? ` · ${new Date(a.scheduled_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}` : ''}</div>
          </div>
          <StatusBadge value={a.status} />
        </div>)}
        {activities.length === 0 && <EmptyState icon={Calendar} title="No programs yet" message="Registered and attended activities will appear here." />}
      </>}
    </div>
  </FamilyShell>
}
