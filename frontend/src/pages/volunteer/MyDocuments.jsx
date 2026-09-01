import { useState, useEffect, useCallback } from 'react'
import { AlertTriangle, FileText, Plus, Upload } from 'lucide-react'
import VolunteerShell from '../../components/volunteer/VolunteerShell'
import Modal from '../../components/admin/Modal'
import StatusBadge from '../../components/admin/StatusBadge'
import { LoadingState, ErrorState, errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch, uploadForm } from '../../lib/api'

const DOCUMENT_TYPES = ['Identification', 'Volunteer Agreement', 'Certificate', 'Training Certificate', 'Other']

const EXPIRY_STYLES = { expired: 'text-red-500', expiring_soon: 'text-amber-500', valid: 'text-kMuted' }
const EXPIRY_LABELS = { expired: 'Expired', expiring_soon: 'Expiring soon', valid: 'Valid' }

function UploadModal({ onClose, onUploaded, showToast }) {
  const [saving, setSaving] = useState(false)
  const [fileName, setFileName] = useState('')

  async function save(e) {
    e.preventDefault()
    const f = new FormData(e.target)
    if (!f.get('file') || !f.get('file').name) { showToast('Choose a file first'); return }
    setSaving(true)
    try {
      await uploadForm('/api/volunteers/me/documents', f)
      showToast('Document uploaded — pending review')
      onUploaded()
      onClose()
    } catch (err) { showToast(errorMessage(err)) }
    finally { setSaving(false) }
  }

  return <Modal title="Upload document" onClose={onClose}>
    <form onSubmit={save} className="grid gap-4">
      <label className="text-sm font-semibold">Title<input name="title" className="input-k mt-2" placeholder="e.g. National ID" required /></label>
      <label className="text-sm font-semibold">Type<select name="document_type" defaultValue={DOCUMENT_TYPES[0]} className="input-k mt-2">{DOCUMENT_TYPES.map(t => <option key={t}>{t}</option>)}</select></label>
      <div className="grid grid-cols-2 gap-4">
        <label className="text-sm font-semibold">Issue date (optional)<input name="issue_date" type="date" className="input-k mt-2" /></label>
        <label className="text-sm font-semibold">Expiry date (optional)<input name="expiry_date" type="date" className="input-k mt-2" /></label>
      </div>
      <label className="text-sm font-semibold">
        File (image or PDF, max 10MB)
        <div className="mt-2 flex items-center gap-3">
          <label className="btn-orange cursor-pointer"><Upload size={15} /> Choose file<input name="file" type="file" accept="image/jpeg,image/png,image/webp,application/pdf" className="hidden" onChange={e => setFileName(e.target.files[0]?.name || '')} /></label>
          {fileName && <span className="truncate text-sm text-kMuted">{fileName}</span>}
        </div>
      </label>
      <button disabled={saving} className="btn-orange mt-2 disabled:opacity-60">{saving ? 'Uploading…' : 'Upload'}</button>
    </form>
  </Modal>
}

export default function MyDocuments({ showToast }) {
  const [documents, setDocuments] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [uploadOpen, setUploadOpen] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try { setDocuments((await apiFetch('/api/volunteers/me/documents')).documents) }
    catch (err) { setError(errorMessage(err)) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  async function remove(doc) {
    if (!window.confirm(`Delete "${doc.title}"?`)) return
    try { await apiFetch(`/api/documents/${doc.id}`, { method: 'DELETE' }); showToast('Document deleted'); load() }
    catch (err) { showToast(errorMessage(err)) }
  }

  return <VolunteerShell>
    <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
      <div><div className="eyebrow">My records</div><h1 className="font-display text-3xl font-bold text-kGreen">My Documents</h1></div>
      <button onClick={() => setUploadOpen(true)} className="btn-orange"><Plus size={16} /> Upload document</button>
    </div>

    {loading ? <LoadingState label="documents" /> : error ? <ErrorState message={error} onRetry={load} /> : <div className="mt-7 grid gap-3">
      {documents.map(d => <div key={d.id} className="card-k p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-kTint text-kOrange"><FileText size={18} /></div>
            <div>
              <div className="font-semibold text-kInk">{d.title}</div>
              <div className="text-xs text-kMuted">{d.document_type} &middot; {d.original_filename}</div>
              {d.expiry_date && <div className={`mt-1 flex items-center gap-1 text-xs font-semibold ${EXPIRY_STYLES[d.expiry_state]}`}>{d.expiry_state !== 'valid' && <AlertTriangle size={11} />} {EXPIRY_LABELS[d.expiry_state]} &middot; {d.expiry_date}</div>}
              {d.status === 'Rejected' && d.rejection_reason && <div className="mt-1 text-xs text-red-500">Reason: {d.rejection_reason}</div>}
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-3">
            <StatusBadge value={d.status} />
            {d.status === 'Pending' && <button onClick={() => remove(d)} className="text-xs font-semibold text-kMuted hover:text-red-600">Delete</button>}
          </div>
        </div>
      </div>)}
      {documents.length === 0 && <div className="card-k p-10 text-center text-sm text-kMuted">No documents uploaded yet.</div>}
    </div>}

    {uploadOpen && <UploadModal onClose={() => setUploadOpen(false)} onUploaded={load} showToast={showToast} />}
  </VolunteerShell>
}
