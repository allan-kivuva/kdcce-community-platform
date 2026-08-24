import { useState, useRef } from 'react'
import { Check, Pencil, ImagePlus, AlertCircle } from 'lucide-react'
import VolunteerShell from '../../components/volunteer/VolunteerShell'
import Modal from '../../components/admin/Modal'
import AssignmentPhoto from '../../components/admin/AssignmentPhoto'
import AssignmentConversation from '../../components/admin/AssignmentConversation'
import { LoadingState, ErrorState, errorMessage } from '../../components/admin/adminHelpers'
import { useApiResource } from '../../lib/useApiResource'
import { apiFetch, uploadFile, ApiError } from '../../lib/api'

const ASSIGNEE_STATUSES = ['In Progress', 'Completed', 'Cancelled']
const PRIORITY_STYLES = { Low: 'bg-kBorderSoft text-kMuted', Medium: 'bg-kTint text-kOrange', High: 'bg-orange-100 text-orange-700', Urgent: 'bg-red-100 text-red-700' }

function UpdateModal({ req, onClose, onSaved, showToast }) {
  const [saving, setSaving] = useState(false)
  const [photoKey, setPhotoKey] = useState(0)
  const fileRef = useRef(null)
  const basePath = `/api/assistance-requests/${req.id}`

  async function save(e) {
    e.preventDefault()
    const f = new FormData(e.target)
    setSaving(true)
    try {
      await onSaved(req.id, { status: f.get('status'), outcome_notes: f.get('outcome_notes') || null })
      const file = fileRef.current?.files?.[0]
      if (file) {
        await uploadFile(`${basePath}/photo`, 'photo', file)
        setPhotoKey(k => k + 1)
        if (fileRef.current) fileRef.current.value = ''
      }
      showToast('Request updated')
    } catch (err) { showToast(err instanceof ApiError ? err.message : errorMessage(err)) }
    finally { setSaving(false) }
  }
  return <Modal title={`${req.elderly_member_name} — ${req.elderly_member_code}`} onClose={onClose}>
    <div className="mb-4 rounded-xl bg-kCream p-3 text-sm text-kMuted">{req.description}</div>
    <form onSubmit={save} className="grid gap-4">
      <label className="text-sm font-semibold">Status<select name="status" defaultValue={ASSIGNEE_STATUSES.includes(req.status) ? req.status : 'In Progress'} className="input-k mt-2">{ASSIGNEE_STATUSES.map(s => <option key={s}>{s}</option>)}</select></label>
      <label className="text-sm font-semibold">Outcome notes<textarea name="outcome_notes" defaultValue={req.outcome_notes} rows={3} className="input-k mt-2" placeholder="What happened, how it went" /></label>

      <div>
        <span className="text-sm font-semibold">Optional photo</span>
        <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp" className="input-k mt-2" />
        <p className="mt-2 flex items-start gap-2 text-xs leading-5 text-kMuted"><AlertCircle size={14} className="mt-0.5 shrink-0" /> Photo upload is optional. Only upload a photo when appropriate and with the required consent. Do not upload sensitive or unrelated images.</p>
        <div className="mt-3"><AssignmentPhoto key={photoKey} basePath={basePath} /></div>
      </div>

      <button disabled={saving} className="btn-orange mt-2 disabled:opacity-60"><ImagePlus size={16} /> {saving ? 'Saving…' : 'Save update'}</button>
    </form>

    <div className="mt-6 border-t border-kBorderSoft pt-5"><AssignmentConversation basePath={basePath} /></div>
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
