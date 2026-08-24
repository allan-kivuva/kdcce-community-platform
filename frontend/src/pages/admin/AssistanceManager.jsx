import { useState, useEffect, useCallback } from 'react'
import { Search, Plus, Pencil } from 'lucide-react'
import Shell from '../../components/admin/Shell'
import Modal from '../../components/admin/Modal'
import AssignmentPhoto from '../../components/admin/AssignmentPhoto'
import AssignmentConversation from '../../components/admin/AssignmentConversation'
import AssignmentReview from '../../components/admin/AssignmentReview'
import { LoadingState, ErrorState, errorMessage } from '../../components/admin/adminHelpers'
import { useApiResource } from '../../lib/useApiResource'
import { apiFetch } from '../../lib/api'

const TYPES = ['Hospital Accompaniment', 'Transportation', 'Food Assistance', 'Companionship', 'Home Support', 'Other']
const PRIORITIES = ['Low', 'Medium', 'High', 'Urgent']
const STATUSES = ['Requested', 'Matching', 'Assigned', 'Accepted', 'Started', 'In Progress', 'Completed', 'Cancelled']
const PRIORITY_STYLES = { Low: 'bg-kBorderSoft text-kMuted', Medium: 'bg-kTint text-kOrange', High: 'bg-orange-100 text-orange-700', Urgent: 'bg-red-100 text-red-700' }

function NewRequestModal({ assignees, onClose, onCreated, showToast }) {
  const [members, setMembers] = useState([])
  const [q, setQ] = useState('')
  const [selected, setSelected] = useState(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => { apiFetch('/api/elderly').then(d => setMembers(d.members)).catch(() => {}) }, [])

  const query = q.trim().toLowerCase()
  const results = query ? members.filter(m => m.full_name.toLowerCase().includes(query) || m.member_id.toLowerCase().includes(query)).slice(0, 8) : []

  async function save(e) {
    e.preventDefault()
    const f = new FormData(e.target)
    const assignedVal = f.get('assigned_to_id')
    setSaving(true)
    try {
      await onCreated({ elderly_member_id: selected.id, request_type: f.get('request_type'), priority: f.get('priority'), description: f.get('description'), assigned_to_id: assignedVal ? Number(assignedVal) : null })
      showToast(assignedVal ? 'Assistance request created and assigned' : 'Assistance request created')
      onClose()
    } catch (err) { showToast(errorMessage(err)) }
    finally { setSaving(false) }
  }

  return <Modal title="New assistance request" onClose={onClose}>
    {!selected ? <div>
      <div className="relative"><Search className="absolute left-3 top-3.5 text-kMuted" size={17} /><input value={q} onChange={e => setQ(e.target.value)} className="input-k pl-10" placeholder="Search elderly member..." autoFocus /></div>
      <div className="mt-3 grid gap-2">
        {results.map(m => <button key={m.id} type="button" onClick={() => setSelected(m)} className="flex items-center justify-between rounded-xl border border-kBorder px-4 py-3 text-left hover:bg-kCream"><div><div className="text-sm font-semibold text-kInk">{m.full_name}</div><div className="text-xs text-kMuted">{m.member_id}</div></div></button>)}
        {query && results.length === 0 && <p className="text-sm text-kMuted">No matching member.</p>}
      </div>
    </div> : <form onSubmit={save} className="grid gap-4">
      <div className="rounded-xl bg-kCream p-3 text-sm"><span className="font-semibold text-kInk">{selected.full_name}</span> <span className="text-kMuted">({selected.member_id})</span> <button type="button" onClick={() => setSelected(null)} className="ml-2 text-xs font-semibold text-kOrange">Change</button></div>
      <div className="grid grid-cols-2 gap-4">
        <label className="text-sm font-semibold">Type<select name="request_type" defaultValue={TYPES[0]} className="input-k mt-2">{TYPES.map(t => <option key={t}>{t}</option>)}</select></label>
        <label className="text-sm font-semibold">Priority<select name="priority" defaultValue="Medium" className="input-k mt-2">{PRIORITIES.map(p => <option key={p}>{p}</option>)}</select></label>
      </div>
      <label className="text-sm font-semibold">Description<textarea name="description" rows={3} className="input-k mt-2" required /></label>
      <label className="text-sm font-semibold">Assign to (optional)<select name="assigned_to_id" defaultValue="" className="input-k mt-2"><option value="">Unassigned for now</option>{assignees.map(a => <option key={a.id} value={a.id}>{a.name} ({a.role})</option>)}</select></label>
      <button disabled={saving} className="btn-orange mt-2 disabled:opacity-60">{saving ? 'Creating…' : 'Create request'}</button>
    </form>}
  </Modal>
}

function EditRequestModal({ req, assignees, onClose, onSaved, showToast }) {
  const [saving, setSaving] = useState(false)
  async function save(e) {
    e.preventDefault()
    const f = new FormData(e.target)
    const assignedVal = f.get('assigned_to_id')
    const data = {
      priority: f.get('priority'), status: f.get('status'),
      assigned_to_id: assignedVal ? Number(assignedVal) : null,
      description: f.get('description'),
      outcome_notes: f.get('outcome_notes') || null,
    }
    setSaving(true)
    try {
      await onSaved(req.id, data)
      showToast('Request updated')
      onClose()
    } catch (err) { showToast(errorMessage(err)) }
    finally { setSaving(false) }
  }
  return <Modal title={`${req.elderly_member_name} — ${req.elderly_member_code}`} onClose={onClose}>
    <form onSubmit={save} className="grid gap-4">
      <div className="grid grid-cols-2 gap-4">
        <label className="text-sm font-semibold">Priority<select name="priority" defaultValue={req.priority} className="input-k mt-2">{PRIORITIES.map(p => <option key={p}>{p}</option>)}</select></label>
        <label className="text-sm font-semibold">Status<select name="status" defaultValue={req.status} className="input-k mt-2">{STATUSES.map(s => <option key={s}>{s}</option>)}</select></label>
      </div>
      <label className="text-sm font-semibold">Assign to<select name="assigned_to_id" defaultValue={req.assigned_to_id || ''} className="input-k mt-2"><option value="">Unassigned</option>{assignees.map(a => <option key={a.id} value={a.id}>{a.name} ({a.role})</option>)}</select></label>
      <label className="text-sm font-semibold">Description<textarea name="description" defaultValue={req.description} rows={2} className="input-k mt-2" required /></label>
      <label className="text-sm font-semibold">Outcome notes<textarea name="outcome_notes" defaultValue={req.outcome_notes} rows={2} className="input-k mt-2" /></label>
      <button disabled={saving} className="btn-orange mt-2 disabled:opacity-60">{saving ? 'Saving…' : 'Save changes'}</button>
    </form>

    <div className="mt-6 border-t border-kBorderSoft pt-5"><span className="text-xs font-bold uppercase tracking-wide text-kMuted">Photo</span><div className="mt-3"><AssignmentPhoto basePath={`/api/assistance-requests/${req.id}`} /></div></div>
    <div className="mt-6 border-t border-kBorderSoft pt-5"><AssignmentReview basePath={`/api/assistance-requests/${req.id}`} status={req.status} showToast={showToast} /></div>
    <div className="mt-6 border-t border-kBorderSoft pt-5"><AssignmentConversation basePath={`/api/assistance-requests/${req.id}`} /></div>
  </Modal>
}

export default function AssistanceManager({ showToast }) {
  const requestsApi = useApiResource('/api/assistance-requests', { listKey: 'requests', itemKey: 'request' })
  const [assignees, setAssignees] = useState([])
  const [statusFilter, setStatusFilter] = useState('All')
  const [priorityFilter, setPriorityFilter] = useState('All')
  const [newModalOpen, setNewModalOpen] = useState(false)
  const [editReq, setEditReq] = useState(null)

  // Reuses the home-visits assignee list — same eligibility rule
  // (staff/admin or a Verified volunteer) applies to both modules.
  useEffect(() => { apiFetch('/api/home-visits/assignees').then(d => setAssignees(d.assignees)).catch(() => {}) }, [])

  const filtered = requestsApi.items.filter(r =>
    (statusFilter === 'All' || r.status === statusFilter) && (priorityFilter === 'All' || r.priority === priorityFilter)
  )

  return <Shell>
    <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
      <div><div className="eyebrow">Manage</div><h1 className="font-display text-3xl font-bold text-kGreen">Assistance requests</h1></div>
      <button onClick={() => setNewModalOpen(true)} className="btn-green"><Plus size={16} /> New request</button>
    </div>

    {requestsApi.loading ? <LoadingState label="requests" /> : requestsApi.error ? <ErrorState message={requestsApi.error} onRetry={requestsApi.reload} /> : <div className="card-k mt-7 overflow-hidden">
      <div className="flex flex-col gap-3 border-b border-kBorderSoft p-5 sm:flex-row">
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="rounded-xl border border-kBorder bg-kSurface px-4 py-3 text-sm text-kInk"><option>All</option>{STATUSES.map(s => <option key={s}>{s}</option>)}</select>
        <select value={priorityFilter} onChange={e => setPriorityFilter(e.target.value)} className="rounded-xl border border-kBorder bg-kSurface px-4 py-3 text-sm text-kInk"><option>All</option>{PRIORITIES.map(p => <option key={p}>{p}</option>)}</select>
      </div>
      <div className="overflow-x-auto"><table className="w-full min-w-[900px] text-left text-sm"><thead className="bg-kBorderSoft text-xs uppercase tracking-wider text-kMuted"><tr><th className="px-5 py-4">Member</th><th className="px-5 py-4">Type</th><th className="px-5 py-4">Priority</th><th className="px-5 py-4">Status</th><th className="px-5 py-4">Assigned to</th><th className="px-5 py-4">Actions</th></tr></thead><tbody>
        {filtered.map(r => <tr key={r.id} className="border-b border-kBorderSoft"><td className="px-5 py-4"><div className="font-semibold text-kInk">{r.elderly_member_name}</div><div className="text-xs text-kMuted">{r.elderly_member_code}</div></td><td className="px-5 py-4 text-kMuted">{r.request_type}</td><td className="px-5 py-4"><span className={`rounded-full px-3 py-1 text-xs font-bold ${PRIORITY_STYLES[r.priority]}`}>{r.priority}</span></td><td className="px-5 py-4 text-kMuted">{r.status}</td><td className="px-5 py-4 text-kMuted">{r.assigned_to || 'Unassigned'}</td><td className="px-5 py-4"><button onClick={() => setEditReq(r)} className="text-kOrange"><Pencil size={16} /></button></td></tr>)}
        {filtered.length === 0 && <tr><td colSpan={6} className="px-5 py-10 text-center text-sm text-kMuted">No requests match your filters.</td></tr>}
      </tbody></table></div>
    </div>}

    {newModalOpen && <NewRequestModal assignees={assignees} onClose={() => setNewModalOpen(false)} onCreated={data => requestsApi.create(data)} showToast={showToast} />}
    {editReq && <EditRequestModal req={editReq} assignees={assignees} onClose={() => setEditReq(null)} onSaved={(id, data) => requestsApi.patch(id, data)} showToast={showToast} />}
  </Shell>
}
