import { useState, useEffect, useCallback } from 'react'
import { Pencil } from 'lucide-react'
import VolunteerShell from '../../components/volunteer/VolunteerShell'
import Modal from '../../components/admin/Modal'
import AssignmentWorkflow from '../../components/volunteer/AssignmentWorkflow'
import AssignmentConversation from '../../components/admin/AssignmentConversation'
import AssignmentReview from '../../components/admin/AssignmentReview'
import { LoadingState, ErrorState, errorMessage } from '../../components/admin/adminHelpers'
import { useVolunteerData } from '../../lib/VolunteerDataContext'
import { apiFetch } from '../../lib/api'

const PRIORITY_STYLES = { Low: 'bg-kBorderSoft text-kMuted', Medium: 'bg-kTint text-kOrange', High: 'bg-orange-100 text-orange-700', Urgent: 'bg-red-100 text-red-700' }

function fmtDate(iso) { return iso ? new Date(iso).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }) : 'Not scheduled yet' }

const WORK_FIELDS = [
  { name: 'observations', label: 'What was done?', placeholder: 'What you observed and did during the visit' },
  { name: 'support_provided', label: 'Outcome', placeholder: 'Support provided / outcome of the visit' },
]

function UpdateModal({ visitId, onClose, onListChanged, showToast }) {
  const [visit, setVisit] = useState(null)
  const basePath = `/api/home-visits/${visitId}`

  const load = useCallback(async () => {
    try { setVisit((await apiFetch(basePath)).visit) } catch (err) { showToast(errorMessage(err)) }
  }, [basePath, showToast])

  useEffect(() => { load() }, [load])

  function refreshed() { load(); onListChanged() }

  if (!visit) return <Modal title="Loading…" onClose={onClose}><LoadingState label="assignment" /></Modal>

  return <Modal title={`${visit.elderly_member_name} — ${visit.elderly_member_code}`} onClose={onClose}>
    <div className="mb-4 rounded-xl bg-kCream p-3 text-sm text-kMuted">{visit.reason}</div>
    <div className="mb-2 flex flex-wrap items-center gap-3 text-sm">
      <span className={`rounded-full px-3 py-1 text-xs font-bold ${PRIORITY_STYLES[visit.priority]}`}>{visit.priority}</span>
      <span className="text-xs font-bold uppercase tracking-wide text-kOrange">{visit.status}</span>
      <span className="text-kMuted">{fmtDate(visit.scheduled_at)}</span>
    </div>

    <AssignmentWorkflow
      basePath={basePath} assignmentType="home_visit" status={visit.status} startedAt={visit.started_at}
      acceptViaEndpoint={false} workFields={WORK_FIELDS} hasChecklist showToast={showToast} onSaved={refreshed}
    />

    <div className="mt-6 border-t border-kBorderSoft pt-5"><AssignmentReview basePath={basePath} status={visit.status} showToast={showToast} /></div>
    <div className="mt-6 border-t border-kBorderSoft pt-5"><AssignmentConversation basePath={basePath} /></div>
  </Modal>
}

export default function MyAssignments({ showToast }) {
  const { visits, loading, error, reload } = useVolunteerData()
  const [editVisitId, setEditVisitId] = useState(null)

  return <VolunteerShell>
    <div><div className="eyebrow">My assignments</div><h1 className="font-display text-3xl font-bold text-kGreen">Home visits</h1></div>

    {loading ? <LoadingState label="assignments" /> : error ? <ErrorState message={error} onRetry={reload} /> : <div className="mt-7 grid gap-4">
      {visits.map(v => <div key={v.id} className="card-k p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2"><span className="font-display text-lg font-bold text-kGreen">{v.elderly_member_name}</span><span className={`rounded-full px-3 py-1 text-xs font-bold ${PRIORITY_STYLES[v.priority]}`}>{v.priority}</span></div>
            <p className="mt-1 text-sm text-kMuted">{v.elderly_member_code} &middot; {fmtDate(v.scheduled_at)}</p>
            <p className="mt-3 text-sm text-kInk">{v.reason}</p>
          </div>
          <div className="flex items-center gap-3"><span className="text-xs font-bold uppercase tracking-wide text-kOrange">{v.status}</span><button onClick={() => setEditVisitId(v.id)} className="text-kOrange"><Pencil size={16} /></button></div>
        </div>
      </div>)}
      {visits.length === 0 && <div className="card-k p-10 text-center text-sm text-kMuted">No home visits assigned to you yet.</div>}
    </div>}

    {editVisitId && <UpdateModal visitId={editVisitId} onClose={() => setEditVisitId(null)} onListChanged={reload} showToast={showToast} />}
  </VolunteerShell>
}
