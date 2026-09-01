import { useEffect, useState } from 'react'
import { Sparkles, UserCheck } from 'lucide-react'
import Shell from '../../components/admin/Shell'
import { LoadingState, ErrorState, EmptyState, errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch } from '../../lib/api'

function ScoreBar({ score }) {
  const pct = Math.max(0, Math.min(100, score))
  return <div className="h-2 w-32 overflow-hidden rounded-full bg-kBorderSoft"><div className="h-full rounded-full bg-kOrange" style={{ width: `${pct}%` }} /></div>
}

function AssignPanel({ volunteerId, memberId, showToast, onCancel, onAssigned }) {
  const [candidates, setCandidates] = useState({ visits: [], requests: [] })
  const [loadingCandidates, setLoadingCandidates] = useState(true)
  const [selectedKind, setSelectedKind] = useState('')
  const [selectedId, setSelectedId] = useState('')
  const [assigning, setAssigning] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoadingCandidates(true)
      try {
        const [visitsRes, requestsRes] = await Promise.all([
          apiFetch(`/api/home-visits?elderly_member_id=${memberId}&status=Pending`),
          apiFetch(`/api/assistance-requests?elderly_member_id=${memberId}&status=Requested`),
        ])
        if (!cancelled) setCandidates({ visits: visitsRes.visits, requests: requestsRes.requests })
      } catch (err) {
        if (!cancelled) { showToast(errorMessage(err)); onCancel() }
      } finally {
        if (!cancelled) setLoadingCandidates(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [memberId]) // eslint-disable-line react-hooks/exhaustive-deps

  async function confirmAssign() {
    if (!selectedKind || !selectedId) return
    setAssigning(true)
    try {
      const path = selectedKind === 'visit' ? `/api/home-visits/${selectedId}` : `/api/assistance-requests/${selectedId}`
      await apiFetch(path, { method: 'PATCH', body: { assigned_to_id: volunteerId, status: 'Assigned' } })
      showToast('Volunteer assigned')
      onAssigned?.()
    } catch (err) { showToast(errorMessage(err)) }
    finally { setAssigning(false) }
  }

  const hasCandidates = candidates.visits.length > 0 || candidates.requests.length > 0

  return <div className="mt-3 rounded-xl border border-kBorderSoft bg-kCream p-4">
    {loadingCandidates && <p className="text-sm text-kMuted">Loading this member's pending visits/requests…</p>}
    {!loadingCandidates && !hasCandidates && <p className="text-sm text-kMuted">This member has no Pending home visits or Requested assistance requests to assign right now — create or open one from the Home Visits / Assistance Requests page first.</p>}
    {!loadingCandidates && hasCandidates && <>
      <p className="text-sm font-semibold text-kInk">Assign this volunteer to:</p>
      <div className="mt-2 grid gap-2">
        {candidates.visits.map(v => <label key={`visit-${v.id}`} className="flex items-center gap-2 text-sm">
          <input type="radio" name={`assign-${volunteerId}`} checked={selectedKind === 'visit' && String(selectedId) === String(v.id)} onChange={() => { setSelectedKind('visit'); setSelectedId(v.id) }} />
          Home visit #{v.id} — {v.reason}
        </label>)}
        {candidates.requests.map(r => <label key={`req-${r.id}`} className="flex items-center gap-2 text-sm">
          <input type="radio" name={`assign-${volunteerId}`} checked={selectedKind === 'request' && String(selectedId) === String(r.id)} onChange={() => { setSelectedKind('request'); setSelectedId(r.id) }} />
          Assistance request #{r.id} — {r.request_type}
        </label>)}
      </div>
      <div className="mt-3 flex items-center gap-3">
        <button disabled={!selectedId || assigning} onClick={confirmAssign} className="btn-orange disabled:opacity-60">{assigning ? 'Assigning…' : 'Confirm assignment'}</button>
        <button onClick={onCancel} className="text-sm font-semibold text-kMuted">Cancel</button>
      </div>
    </>}
  </div>
}

function VolunteerRow({ volunteer, memberId, showToast, onAssigned }) {
  const [confirming, setConfirming] = useState(false)
  return <div className="card-k p-5">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div>
        <div className="font-semibold text-kInk">{volunteer.name}</div>
        <div className="mt-1 flex items-center gap-2 text-xs text-kMuted">
          <span>Score {volunteer.score}</span>
          <ScoreBar score={volunteer.score} />
        </div>
      </div>
      <div className="flex items-center gap-4 text-xs text-kMuted">
        <span>{volunteer.distance_km != null ? `${volunteer.distance_km} km away` : 'Distance unknown'}</span>
        <span>{volunteer.workload} active assignment(s)</span>
        <button onClick={() => setConfirming(c => !c)} className="btn-orange text-xs"><UserCheck size={14} /> Assign</button>
      </div>
    </div>
    <div className="mt-3 flex flex-wrap gap-2">
      {volunteer.reasons.map((reason, i) => <span key={i} className="rounded-full bg-kTint px-2.5 py-1 text-xs font-semibold text-kOrange">{reason}</span>)}
    </div>
    {confirming && <AssignPanel volunteerId={volunteer.volunteer_id} memberId={memberId} showToast={showToast} onCancel={() => setConfirming(false)} onAssigned={() => { setConfirming(false); onAssigned?.() }} />}
  </div>
}

export default function SmartMatching({ showToast }) {
  const [members, setMembers] = useState([])
  const [memberId, setMemberId] = useState('')
  const [requestType, setRequestType] = useState('')
  const [date, setDate] = useState('')

  const [volunteers, setVolunteers] = useState([])
  const [searched, setSearched] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    apiFetch('/api/elderly?status=Active').then(d => setMembers(d.members)).catch(() => {})
  }, [])

  async function findVolunteers() {
    if (!memberId) return
    setLoading(true)
    setError('')
    setSearched(true)
    try {
      const params = new URLSearchParams({ member_id: memberId })
      if (requestType) params.set('request_type', requestType)
      if (date) params.set('date', date)
      const data = await apiFetch(`/api/matching/volunteers?${params.toString()}`)
      setVolunteers(data.volunteers)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return <Shell>
    <div><div className="eyebrow">Operations</div><h1 className="font-display text-3xl font-bold text-kGreen">Smart Matching</h1></div>
    <p className="mt-2 max-w-2xl text-sm text-kMuted">Rank verified volunteers for an elderly member by availability, skills, distance, and current workload — a recommendation only, assignment is always a separate, explicit step.</p>

    <div className="card-k mt-6 p-5">
      <div className="grid gap-4 sm:grid-cols-3">
        <label className="text-sm font-semibold">Elderly member
          <select value={memberId} onChange={e => { setMemberId(e.target.value); setSearched(false) }} className="input-k mt-2">
            <option value="">Select a member…</option>
            {members.map(m => <option key={m.id} value={m.id}>{m.full_name} ({m.member_id})</option>)}
          </select>
        </label>
        <label className="text-sm font-semibold">Request type / skill (optional)
          <input value={requestType} onChange={e => setRequestType(e.target.value)} placeholder="e.g. Medical, Transport" className="input-k mt-2" />
        </label>
        <label className="text-sm font-semibold">Date (optional)
          <input type="date" value={date} onChange={e => setDate(e.target.value)} className="input-k mt-2" />
        </label>
      </div>
      <button disabled={!memberId || loading} onClick={findVolunteers} className="btn-orange mt-4 disabled:opacity-60"><Sparkles size={16} /> {loading ? 'Finding…' : 'Find volunteers'}</button>
    </div>

    {loading && <LoadingState label="matches" rows={3} />}
    {!loading && error && <ErrorState message={error} onRetry={findVolunteers} />}
    {!loading && !error && searched && volunteers.length === 0 && <EmptyState icon={Sparkles} title="No eligible volunteers" message="No verified, available volunteers matched this member with the current filters." />}
    {!loading && !error && !searched && <EmptyState icon={Sparkles} title="Choose a member to get started" message="Select an elderly member above, then click Find volunteers." />}

    {!loading && !error && volunteers.length > 0 && <div className="mt-6 grid gap-4">
      {volunteers.map(v => <VolunteerRow key={v.volunteer_id} volunteer={v} memberId={memberId} showToast={showToast} onAssigned={findVolunteers} />)}
    </div>}
  </Shell>
}
