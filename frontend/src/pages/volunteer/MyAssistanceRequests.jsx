import { useState } from 'react'
import { Check, Pencil } from 'lucide-react'
import VolunteerShell from '../../components/volunteer/VolunteerShell'
import Modal from '../../components/admin/Modal'
import { LoadingState, ErrorState, errorMessage } from '../../components/admin/adminHelpers'
import { useApiResource } from '../../lib/useApiResource'
import { apiFetch } from '../../lib/api'

const ASSIGNEE_STATUSES = ['In Progress', 'Completed', 'Cancelled']
const PRIORITY_STYLES = { Low: 'bg-kBorderSoft text-kMuted', Medium: 'bg-kTint text-kOrange', High: 'bg-orange-100 text-orange-700', Urgent: 'bg-red-100 text-red-700' }

function UpdateModal({ req, onClose, onSaved, showToast }) {
  const [saving, setSaving] = useState(false)
  async function save(e) {
    e.preventDefault()
    const f = new FormData(e.target)
    setSaving(true)
    try {
      await onSaved(req.id, { status: f.get('status'), outcome_notes: f.get('outcome_notes') || null })
      showToast('Request updated')
      onClose()
    } catch (err) { showToast(errorMessage(err)) }
    finally { setSaving(false) }
  }
  return <Modal title={`${req.elderly_member_name} — ${req.elderly_member_code}`} onClose={onClose}>
    <div className="mb-4 rounded-xl bg-kCream p-3 text-sm text-kMuted">{req.description}</div>
    <form onSubmit={save} className="grid gap-4">
      <label className="text-sm font-semibold">Status<select name="status" defaultValue={ASSIGNEE_STATUSES.includes(req.status) ? req.status : 'In Progress'} className="input-k mt-2">{ASSIGNEE_STATUSES.map(s => <option key={s}>{s}</option>)}</select></label>
      <label className="text-sm font-semibold">Outcome notes<textarea name="outcome_notes" defaultValue={req.outcome_notes} rows={3} className="input-k mt-2" placeholder="What happened, how it went" /></label>
      <button disabled={saving} className="btn-orange mt-2 disabled:opacity-60">{saving ? 'Saving…' : 'Save update'}</button>
    </form>
  </Modal>
}

export default function MyAssistanceRequests({ showToast }) {
  const requestsApi = useApiResource('/api/assistance-requests', { listKey: 'requests', itemKey: 'request' })
  const [editReq, setEditReq] = useState(null)
  const [acceptingId, setAcceptingId] = useState(null)

  async function accept(req) {
    setAcceptingId(req.id)
    try {
      await apiFetch(`/api/assistance-requests/${req.id}/accept`, { method: 'POST' })
      showToast(`Accepted — ${req.elderly_member_name}`)
      requestsApi.reload()
    } catch (err) { showToast(errorMessage(err)) }
    finally { setAcceptingId(null) }
  }

  return <VolunteerShell>
    <div><div className="eyebrow">My assignments</div><h1 className="font-display text-3xl font-bold text-kGreen">Assistance requests</h1></div>

    {requestsApi.loading ? <LoadingState label="requests" /> : requestsApi.error ? <ErrorState message={requestsApi.error} onRetry={requestsApi.reload} /> : <div className="mt-7 grid gap-4">
      {requestsApi.items.map(r => <div key={r.id} className="card-k p-5">
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
              : <button onClick={() => setEditReq(r)} className="text-kOrange"><Pencil size={16} /></button>}
          </div>
        </div>
      </div>)}
      {requestsApi.items.length === 0 && <div className="card-k p-10 text-center text-sm text-kMuted">No assistance requests assigned to you yet.</div>}
    </div>}

    {editReq && <UpdateModal req={editReq} onClose={() => setEditReq(null)} onSaved={(id, data) => requestsApi.patch(id, data)} showToast={showToast} />}
  </VolunteerShell>
}
