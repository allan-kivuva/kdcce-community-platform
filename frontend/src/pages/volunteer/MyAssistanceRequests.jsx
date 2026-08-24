import { useState, useEffect, useCallback } from 'react'
import { Check, Pencil } from 'lucide-react'
import VolunteerShell from '../../components/volunteer/VolunteerShell'
import Modal from '../../components/admin/Modal'
import AssignmentWorkflow from '../../components/volunteer/AssignmentWorkflow'
import AssignmentConversation from '../../components/admin/AssignmentConversation'
import AssignmentReview from '../../components/admin/AssignmentReview'
import { LoadingState, ErrorState, errorMessage } from '../../components/admin/adminHelpers'
import { useVolunteerData } from '../../lib/VolunteerDataContext'
import { apiFetch } from '../../lib/api'

const PRIORITY_STYLES = { Low: 'bg-kBorderSoft text-kMuted', Medium: 'bg-kTint text-kOrange', High: 'bg-orange-100 text-orange-700', Urgent: 'bg-red-100 text-red-700' }

const WORK_FIELDS = [
  { name: 'outcome_notes', label: 'What was done / Outcome', placeholder: 'What happened, how it went', rows: 3 },
]

function UpdateModal({ reqId, onClose, onListChanged, showToast }) {
  const [req, setReq] = useState(null)
  const basePath = `/api/assistance-requests/${reqId}`

  const load = useCallback(async () => {
    try { setReq((await apiFetch(basePath)).request) } catch (err) { showToast(errorMessage(err)) }
  }, [basePath, showToast])

  useEffect(() => { load() }, [load])

  function refreshed() { load(); onListChanged() }

  if (!req) return <Modal title="Loading…" onClose={onClose}><LoadingState label="assignment" /></Modal>

  return <Modal title={`${req.elderly_member_name} — ${req.elderly_member_code}`} onClose={onClose}>
    <div className="mb-4 rounded-xl bg-kCream p-3 text-sm text-kMuted">{req.description}</div>
    <div className="mb-2 flex flex-wrap items-center gap-3 text-sm">
      <span className={`rounded-full px-3 py-1 text-xs font-bold ${PRIORITY_STYLES[req.priority]}`}>{req.priority}</span>
      <span className="text-xs font-bold uppercase tracking-wide text-kOrange">{req.status}</span>
      <span className="text-kMuted">{req.request_type}</span>
    </div>

    <AssignmentWorkflow
      basePath={basePath} assignmentType="assistance_request" status={req.status} startedAt={req.started_at}
      acceptViaEndpoint workFields={WORK_FIELDS} hasChecklist={false} showToast={showToast} onSaved={refreshed}
    />

    <div className="mt-6 border-t border-kBorderSoft pt-5"><AssignmentReview basePath={basePath} status={req.status} showToast={showToast} /></div>
    <div className="mt-6 border-t border-kBorderSoft pt-5"><AssignmentConversation basePath={basePath} /></div>
  </Modal>
}

export default function MyAssistanceRequests({ showToast }) {
  const { requests, loading, error, reload } = useVolunteerData()
  const [editReqId, setEditReqId] = useState(null)
  const [acceptingId, setAcceptingId] = useState(null)

  async function accept(req) {
    setAcceptingId(req.id)
    try {
      await apiFetch(`/api/assistance-requests/${req.id}/accept`, { method: 'POST' })
      showToast(`Accepted — ${req.elderly_member_name}`)
      reload()
    } catch (err) { showToast(errorMessage(err)) }
    finally { setAcceptingId(null) }
  }

  return <VolunteerShell>
    <div><div className="eyebrow">My assignments</div><h1 className="font-display text-3xl font-bold text-kGreen">Assistance requests</h1></div>

    {loading ? <LoadingState label="requests" /> : error ? <ErrorState message={error} onRetry={reload} /> : <div className="mt-7 grid gap-4">
      {requests.map(r => <div key={r.id} className="card-k p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2"><span className="font-display text-lg font-bold text-kGreen">{r.elderly_member_name}</span><span className={`rounded-full px-3 py-1 text-xs font-bold ${PRIORITY_STYLES[r.priority]}`}>{r.priority}</span></div>
            <p className="mt-1 text-sm text-kMuted">{r.request_type} &middot; {r.elderly_member_code}</p>
            <p className="mt-3 text-sm text-kInk">{r.description}</p>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs font-bold uppercase tracking-wide text-kOrange">{r.status}</span>
            {r.status === 'Assigned'
              ? <button disabled={acceptingId === r.id} onClick={() => accept(r)} className="btn-green disabled:opacity-60"><Check size={15} /> Accept</button>
              : <button onClick={() => setEditReqId(r.id)} className="text-kOrange"><Pencil size={16} /></button>}
          </div>
        </div>
      </div>)}
      {requests.length === 0 && <div className="card-k p-10 text-center text-sm text-kMuted">No assistance requests assigned to you yet.</div>}
    </div>}

    {editReqId && <UpdateModal reqId={editReqId} onClose={() => setEditReqId(null)} onListChanged={reload} showToast={showToast} />}
  </VolunteerShell>
}
