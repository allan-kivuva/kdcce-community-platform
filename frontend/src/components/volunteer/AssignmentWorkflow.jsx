import { useState, useEffect, useCallback, useRef } from 'react'
import { CheckCircle2, Circle, Clock, ImagePlus, AlertCircle } from 'lucide-react'
import AssignmentPhoto from '../admin/AssignmentPhoto'
import { errorMessage } from '../admin/adminHelpers'
import { apiFetch, uploadFile, ApiError } from '../../lib/api'

function fmtTime(iso) {
  return iso ? new Date(iso).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }) : null
}

// Shared lifecycle UI for a HomeVisit or AssistanceRequest, from the
// volunteer's side: Accept -> Start -> (checklist, home visits only) ->
// Completion Report. Reuses the existing PATCH .../<id> (assignee-scoped
// schema, server-stamps started_at/completed_at) and the existing
// AssistanceRequest accept endpoint — no new assignment-status machinery
// beyond what homevisits/assistance routes.py already added.
export default function AssignmentWorkflow({
  basePath, assignmentType, status, startedAt, acceptViaEndpoint, workFields, hasChecklist, onSaved, showToast,
}) {
  const [busy, setBusy] = useState(false)
  const [showComplete, setShowComplete] = useState(false)
  const [checklist, setChecklist] = useState(null)
  const fileRef = useRef(null)
  const [photoKey, setPhotoKey] = useState(0)

  const loadChecklist = useCallback(async () => {
    if (!hasChecklist) return
    try { setChecklist((await apiFetch(`${basePath}/checklist`)).checklist) } catch { setChecklist(null) }
  }, [basePath, hasChecklist])

  useEffect(() => { loadChecklist() }, [loadChecklist])

  const preAcceptStatuses = assignmentType === 'home_visit' ? ['Pending', 'Assigned'] : ['Requested', 'Matching', 'Assigned']
  const canAccept = preAcceptStatuses.includes(status)
  const canStart = status === 'Accepted'
  const canWorkOn = ['Started', 'In Progress'].includes(status)
  const isDone = status === 'Completed'

  async function accept() {
    setBusy(true)
    try {
      if (acceptViaEndpoint) await apiFetch(`${basePath}/accept`, { method: 'POST' })
      else await apiFetch(basePath, { method: 'PATCH', body: { status: 'Accepted' } })
      showToast('Assignment accepted')
      onSaved()
    } catch (err) { showToast(errorMessage(err)) } finally { setBusy(false) }
  }

  async function start() {
    setBusy(true)
    try {
      await apiFetch(basePath, { method: 'PATCH', body: { status: 'Started' } })
      showToast('Assignment started')
      onSaved()
    } catch (err) { showToast(errorMessage(err)) } finally { setBusy(false) }
  }

  async function toggleChecklistItem(item_key, checked) {
    try { setChecklist((await apiFetch(`${basePath}/checklist`, { method: 'PATCH', body: { item_key, checked } })).checklist) }
    catch (err) { showToast(errorMessage(err)) }
  }

  async function submitCompletion(e) {
    e.preventDefault()
    const f = new FormData(e.target)
    const data = { status: 'Completed' }
    for (const field of workFields) data[field.name] = f.get(field.name) || null
    data.follow_up_required = f.get('follow_up_required') === 'on'
    data.follow_up_notes = f.get('follow_up_notes') || null

    setBusy(true)
    try {
      await apiFetch(basePath, { method: 'PATCH', body: data })
      const file = fileRef.current?.files?.[0]
      if (file) { await uploadFile(`${basePath}/photo`, 'photo', file); setPhotoKey(k => k + 1) }
      showToast('Assignment completed')
      setShowComplete(false)
      onSaved()
    } catch (err) { showToast(err instanceof ApiError ? err.message : errorMessage(err)) } finally { setBusy(false) }
  }

  return <div>
    <h3 className="text-xs font-bold uppercase tracking-wide text-kMuted">Assignment workflow</h3>

    <div className="mt-3 flex flex-wrap items-center gap-2">
      {canAccept && <button disabled={busy} onClick={accept} className="btn-orange disabled:opacity-60">Accept Assignment</button>}
      {canStart && <button disabled={busy} onClick={start} className="btn-orange disabled:opacity-60">Start Assignment</button>}
      {startedAt && <span className="flex items-center gap-1.5 text-sm text-kMuted"><Clock size={14} /> Started: {fmtTime(startedAt)}</span>}
      {canWorkOn && !showComplete && <button disabled={busy} onClick={() => setShowComplete(true)} className="btn-green disabled:opacity-60">Complete Assignment</button>}
      {isDone && <span className="flex items-center gap-1.5 text-sm font-semibold text-kGreen"><CheckCircle2 size={15} /> Completed</span>}
    </div>

    {hasChecklist && checklist && (status !== 'Pending' && status !== 'Requested') && <div className="mt-4 rounded-xl border border-kBorderSoft p-4">
      <h4 className="text-sm font-bold text-kInk">Home Visit Checklist</h4>
      <div className="mt-3 grid gap-2">
        {checklist.map(item => <label key={item.item_key} className="flex cursor-pointer items-center gap-2 text-sm text-kInk">
          <button type="button" onClick={() => toggleChecklistItem(item.item_key, !item.checked)} className="shrink-0">
            {item.checked ? <CheckCircle2 size={18} className="text-kGreen" /> : <Circle size={18} className="text-kBorderSoft" />}
          </button>
          <span className={item.checked ? 'text-kMuted line-through' : ''}>{item.label}</span>
        </label>)}
      </div>
    </div>}

    {showComplete && <form onSubmit={submitCompletion} className="mt-4 grid gap-4 rounded-xl border border-kBorderSoft p-4">
      <h4 className="text-sm font-bold text-kInk">Completion Report</h4>
      {workFields.map(field => <label key={field.name} className="text-sm font-semibold">{field.label}<textarea name={field.name} rows={field.rows || 2} className="input-k mt-2" placeholder={field.placeholder} /></label>)}
      <div>
        <span className="text-sm font-semibold">Follow-up required?</span>
        <div className="mt-2 flex gap-5 text-sm">
          <label className="flex items-center gap-2"><input type="radio" name="follow_up_required" value="off" defaultChecked className="h-4 w-4" onChange={() => {}} /> No</label>
          <label className="flex items-center gap-2"><input type="checkbox" name="follow_up_required" className="h-4 w-4" /> Yes</label>
        </div>
      </div>
      <label className="text-sm font-semibold">Follow-up notes<textarea name="follow_up_notes" rows={2} className="input-k mt-2" placeholder="What needs following up, and when" /></label>
      <div>
        <span className="text-sm font-semibold">Proof of work — Optional photo</span>
        <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp" className="input-k mt-2" />
        <p className="mt-2 flex items-start gap-2 text-xs leading-5 text-kMuted"><AlertCircle size={14} className="mt-0.5 shrink-0" /> Optional — never required. Do not photograph an elderly person without their appropriate consent, and avoid sensitive or identifying images.</p>
        <div className="mt-3"><AssignmentPhoto key={photoKey} basePath={basePath} /></div>
      </div>
      <div className="flex gap-3">
        <button disabled={busy} className="btn-green w-fit disabled:opacity-60"><ImagePlus size={16} /> {busy ? 'Submitting…' : 'Submit Completion'}</button>
        <button type="button" onClick={() => setShowComplete(false)} className="text-sm font-semibold text-kMuted">Cancel</button>
      </div>
    </form>}
  </div>
}
