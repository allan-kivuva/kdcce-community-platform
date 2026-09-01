import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Calendar, MessageSquare, Sparkles, UserRound } from 'lucide-react'
import FamilyShell from '../../components/family/FamilyShell'
import { LoadingState, ErrorState, EmptyState, errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch } from '../../lib/api'

function MemberCard({ member, visits, updates, programs }) {
  const nextVisit = visits.visits.find(v => v.status !== 'Completed' && v.status !== 'Cancelled' && v.scheduled_at)

  return <div className="grid gap-6">
    <div className="card-k p-6">
      <div className="eyebrow">Your family member</div>
      <h1 className="mt-1 font-display text-3xl font-bold text-kGreen">{member.full_name}</h1>
      <p className="mt-1 text-sm text-kMuted">Your relationship: {member.relationship}</p>
    </div>

    <div className="grid gap-6 md:grid-cols-2">
      <div className="card-k p-6">
        <h2 className="flex items-center gap-2 font-display text-lg font-bold text-kGreen"><Calendar size={18} /> Next visit</h2>
        {nextVisit ? (
          <p className="mt-3 text-sm text-kInk">{new Date(nextVisit.scheduled_at).toLocaleString([], { dateStyle: 'full', timeStyle: 'short' })}</p>
        ) : <p className="mt-3 text-sm text-kMuted">No upcoming visit scheduled right now.</p>}
      </div>

      <div className="card-k p-6">
        <h2 className="flex items-center gap-2 font-display text-lg font-bold text-kGreen"><Sparkles size={18} /> Recent updates</h2>
        <div className="mt-3 grid gap-2">
          {updates.updates.slice(0, 4).map((u, i) => <div key={i} className="text-sm text-kInk">{u.label} <span className="text-xs text-kMuted">&middot; {new Date(u.at).toLocaleDateString([], { dateStyle: 'medium' })}</span></div>)}
          {updates.updates.length === 0 && <p className="text-sm text-kMuted">No recent updates yet.</p>}
        </div>
      </div>
    </div>

    <div className="card-k p-6">
      <h2 className="font-display text-lg font-bold text-kGreen">Upcoming programs &amp; events</h2>
      <div className="mt-3 grid gap-2">
        {programs.activities.filter(a => a.status === 'Registered').slice(0, 4).map(a => (
          <div key={a.id} className="rounded-xl bg-kCream px-4 py-3 text-sm">
            <span className="font-semibold text-kInk">{a.title}</span>
            {a.scheduled_at && <span className="ml-2 text-xs text-kMuted">{new Date(a.scheduled_at).toLocaleDateString([], { dateStyle: 'medium' })}</span>}
          </div>
        ))}
        {programs.activities.filter(a => a.status === 'Registered').length === 0 && <p className="text-sm text-kMuted">Nothing registered right now.</p>}
      </div>
    </div>

    <Link to="/family/messages" className="btn-orange w-fit"><MessageSquare size={16} /> Contact care team</Link>
  </div>
}

export default function FamilyOverview() {
  const [members, setMembers] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [detail, setDetail] = useState(null)
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
    let cancelled = false
    async function loadDetail() {
      try {
        const [member, visits, updates, programs] = await Promise.all([
          apiFetch(`/api/family/members/${selectedId}`),
          apiFetch(`/api/family/members/${selectedId}/visits`),
          apiFetch(`/api/family/members/${selectedId}/updates`),
          apiFetch(`/api/family/members/${selectedId}/programs`),
        ])
        if (!cancelled) setDetail({ member: member.member, visits, updates, programs })
      } catch (err) { if (!cancelled) setError(errorMessage(err)) }
    }
    loadDetail()
    return () => { cancelled = true }
  }, [selectedId])

  if (loading) return <FamilyShell><LoadingState label="your family portal" /></FamilyShell>
  if (error) return <FamilyShell><ErrorState message={error} onRetry={load} /></FamilyShell>
  if (members.length === 0) return <FamilyShell><EmptyState icon={UserRound} title="No linked family members yet" message="Once KDCCE staff link your account to a family member, they'll appear here." /></FamilyShell>

  return <FamilyShell>
    {members.length > 1 && (
      <div className="mb-6 flex flex-wrap gap-2">
        {members.map(m => <button key={m.id} onClick={() => { setDetail(null); setSelectedId(m.id) }} className={`rounded-full px-4 py-2 text-sm font-bold ${selectedId === m.id ? 'bg-kGreen text-white' : 'bg-kTint text-kInk'}`}>{m.full_name}</button>)}
      </div>
    )}
    {!detail ? <LoadingState label="member details" /> : <MemberCard {...detail} />}
  </FamilyShell>
}
