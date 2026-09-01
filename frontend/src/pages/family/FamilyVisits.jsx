import { useCallback, useEffect, useState } from 'react'
import { Home } from 'lucide-react'
import FamilyShell from '../../components/family/FamilyShell'
import StatusBadge from '../../components/admin/StatusBadge'
import { LoadingState, ErrorState, EmptyState, errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch } from '../../lib/api'

function VisitRow({ label, status, scheduledAt, completedAt, assignedVolunteerName }) {
  return <div className="card-k flex items-center justify-between gap-4 p-5">
    <div>
      <div className="font-semibold text-kInk">{label}</div>
      <div className="mt-1 text-xs text-kMuted">
        {scheduledAt && `Scheduled ${new Date(scheduledAt).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}`}
        {completedAt && ` · Completed ${new Date(completedAt).toLocaleDateString([], { dateStyle: 'medium' })}`}
        {assignedVolunteerName && ` · With ${assignedVolunteerName}`}
      </div>
    </div>
    <StatusBadge value={status} />
  </div>
}

export default function FamilyVisits() {
  const [members, setMembers] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [data, setData] = useState(null)
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
    apiFetch(`/api/family/members/${selectedId}/visits`).then(setData).catch(err => setError(errorMessage(err)))
  }, [selectedId])

  if (loading) return <FamilyShell><LoadingState label="visits" /></FamilyShell>
  if (error) return <FamilyShell><ErrorState message={error} onRetry={load} /></FamilyShell>
  if (members.length === 0) return <FamilyShell><EmptyState icon={Home} title="No linked family members yet" /></FamilyShell>

  return <FamilyShell>
    <div><div className="eyebrow">Care team</div><h1 className="font-display text-3xl font-bold text-kGreen">Visits</h1></div>
    {members.length > 1 && (
      <div className="mt-4 flex flex-wrap gap-2">
        {members.map(m => <button key={m.id} onClick={() => setSelectedId(m.id)} className={`rounded-full px-4 py-2 text-sm font-bold ${selectedId === m.id ? 'bg-kGreen text-white' : 'bg-kTint text-kInk'}`}>{m.full_name}</button>)}
      </div>
    )}
    <div className="mt-6 grid gap-3">
      {!data ? <LoadingState label="visits" /> : <>
        {data.visits.map(v => <VisitRow key={`visit-${v.id}`} label="Home visit" status={v.status} scheduledAt={v.scheduled_at} completedAt={v.completed_at} assignedVolunteerName={v.assigned_volunteer_name} />)}
        {data.assistance_requests.map(r => <VisitRow key={`req-${r.id}`} label={r.request_type} status={r.status} scheduledAt={r.scheduled_at} completedAt={r.completed_at} assignedVolunteerName={r.assigned_volunteer_name} />)}
        {data.visits.length === 0 && data.assistance_requests.length === 0 && <EmptyState icon={Home} title="No visits yet" message="Scheduled and completed visits will appear here." />}
      </>}
    </div>
  </FamilyShell>
}
