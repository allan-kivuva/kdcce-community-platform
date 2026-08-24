import { useState, useRef } from 'react'
import { Pencil, ImagePlus, AlertCircle } from 'lucide-react'
import VolunteerShell from '../../components/volunteer/VolunteerShell'
import Modal from '../../components/admin/Modal'
import AssignmentPhoto from '../../components/admin/AssignmentPhoto'
import AssignmentConversation from '../../components/admin/AssignmentConversation'
import AssignmentReview from '../../components/admin/AssignmentReview'
import { LoadingState, ErrorState, errorMessage } from '../../components/admin/adminHelpers'
import { useApiResource } from '../../lib/useApiResource'
import { uploadFile, ApiError } from '../../lib/api'

const STATUSES = ['Assigned', 'Scheduled', 'In Progress', 'Completed', 'Cancelled']
const PRIORITY_STYLES = { Low: 'bg-kBorderSoft text-kMuted', Medium: 'bg-kTint text-kOrange', High: 'bg-orange-100 text-orange-700', Urgent: 'bg-red-100 text-red-700' }

function fmtDate(iso) { return iso ? new Date(iso).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }) : 'Not scheduled yet' }

function UpdateModal({ visit, onClose, onSaved, showToast }) {
  const [saving, setSaving] = useState(false)
  const [photoKey, setPhotoKey] = useState(0) // bump to force AssignmentPhoto to refetch after upload
  const fileRef = useRef(null)
  const basePath = `/api/home-visits/${visit.id}`

  async function save(e) {
    e.preventDefault()
    const f = new FormData(e.target)
    const data = {
      status: f.get('status'),
      observations: f.get('observations') || null,
      support_provided: f.get('support_provided') || null,
      follow_up_required: f.get('follow_up_required') === 'on',
      follow_up_notes: f.get('follow_up_notes') || null,
    }
    setSaving(true)
    try {
      await onSaved(visit.id, data)
      const file = fileRef.current?.files?.[0]
      if (file) {
        await uploadFile(`${basePath}/photo`, 'photo', file)
        setPhotoKey(k => k + 1)
        if (fileRef.current) fileRef.current.value = ''
      }
      showToast('Visit updated')
    } catch (err) { showToast(err instanceof ApiError ? err.message : errorMessage(err)) }
    finally { setSaving(false) }
  }

  return <Modal title={`${visit.elderly_member_name} — ${visit.elderly_member_code}`} onClose={onClose}>
    <div className="mb-4 rounded-xl bg-kCream p-3 text-sm text-kMuted">{visit.reason}</div>
    <form onSubmit={save} className="grid gap-4">
      <label className="text-sm font-semibold">Status<select name="status" defaultValue={visit.status} className="input-k mt-2">{STATUSES.map(s => <option key={s}>{s}</option>)}</select></label>
      <label className="text-sm font-semibold">Observations<textarea name="observations" defaultValue={visit.observations} rows={2} className="input-k mt-2" placeholder="What you observed during the visit" /></label>
      <label className="text-sm font-semibold">Support provided<textarea name="support_provided" defaultValue={visit.support_provided} rows={2} className="input-k mt-2" /></label>
      <label className="flex items-center gap-2 text-sm font-semibold"><input name="follow_up_required" type="checkbox" defaultChecked={visit.follow_up_required} className="h-5 w-5" /> Follow-up required</label>
      <label className="text-sm font-semibold">Follow-up notes<textarea name="follow_up_notes" defaultValue={visit.follow_up_notes} rows={2} className="input-k mt-2" /></label>

      <div>
        <span className="text-sm font-semibold">Optional photo</span>
        <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp" className="input-k mt-2" />
        <p className="mt-2 flex items-start gap-2 text-xs leading-5 text-kMuted"><AlertCircle size={14} className="mt-0.5 shrink-0" /> Photo upload is optional. Only upload a photo when appropriate and with the required consent. Do not upload sensitive or unrelated images.</p>
        <div className="mt-3"><AssignmentPhoto key={photoKey} basePath={basePath} /></div>
      </div>

      <button disabled={saving} className="btn-orange mt-2 disabled:opacity-60"><ImagePlus size={16} /> {saving ? 'Saving…' : 'Save update'}</button>
    </form>

    <div className="mt-6 border-t border-kBorderSoft pt-5"><AssignmentReview basePath={basePath} status={visit.status} showToast={showToast} /></div>
    <div className="mt-6 border-t border-kBorderSoft pt-5"><AssignmentConversation basePath={basePath} /></div>
  </Modal>
}

export default function MyAssignments({ showToast }) {
  const visitsApi = useApiResource('/api/home-visits', { listKey: 'visits', itemKey: 'visit' })
  const [editVisit, setEditVisit] = useState(null)

  return <VolunteerShell>
    <div><div className="eyebrow">My assignments</div><h1 className="font-display text-3xl font-bold text-kGreen">Home visits</h1></div>

    {visitsApi.loading ? <LoadingState label="assignments" /> : visitsApi.error ? <ErrorState message={visitsApi.error} onRetry={visitsApi.reload} /> : <div className="mt-7 grid gap-4">
      {visitsApi.items.map(v => <div key={v.id} className="card-k p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2"><span className="font-display text-lg font-bold text-kGreen">{v.elderly_member_name}</span><span className={`rounded-full px-3 py-1 text-xs font-bold ${PRIORITY_STYLES[v.priority]}`}>{v.priority}</span></div>
            <p className="mt-1 text-sm text-kMuted">{v.elderly_member_code} &middot; {fmtDate(v.scheduled_at)}</p>
            <p className="mt-3 text-sm text-kInk">{v.reason}</p>
          </div>
          <div className="flex items-center gap-3"><span className="text-xs font-bold uppercase tracking-wide text-kOrange">{v.status}</span><button onClick={() => setEditVisit(v)} className="text-kOrange"><Pencil size={16} /></button></div>
        </div>
      </div>)}
      {visitsApi.items.length === 0 && <div className="card-k p-10 text-center text-sm text-kMuted">No home visits assigned to you yet.</div>}
    </div>}

    {editVisit && <UpdateModal visit={editVisit} onClose={() => setEditVisit(null)} onSaved={(id, data) => visitsApi.patch(id, data)} showToast={showToast} />}
  </VolunteerShell>
}
