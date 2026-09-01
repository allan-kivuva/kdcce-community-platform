import { useState, useEffect, useCallback } from 'react'
import { Search, Plus, Pencil, AlertTriangle } from 'lucide-react'
import Shell from '../../components/admin/Shell'
import Modal from '../../components/admin/Modal'
import StatusBadge from '../../components/admin/StatusBadge'
import { LoadingState, ErrorState, errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch } from '../../lib/api'

const STATUSES = ['Pending', 'In Progress', 'Completed']
const PRIORITIES = ['Low', 'Medium', 'High', 'Urgent']
const SOURCE_LABELS = { health_record: 'Health', home_visit: 'Home Visit', assistance_request: 'Assistance', incident: 'Incident', manual: 'Manual' }

function NewFollowUpModal({ assignees, onClose, onCreated, showToast }) {
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
      await onCreated({
        elderly_member_id: selected.id, reason: f.get('reason'), priority: f.get('priority'),
        assigned_to_id: assignedVal ? Number(assignedVal) : null, due_date: f.get('due_date') || null,
      })
      showToast('Follow-up created')
      onClose()
    } catch (err) { showToast(errorMessage(err)) }
    finally { setSaving(false) }
  }

  return <Modal title="New follow-up" onClose={onClose}>
    {!selected ? <div>
      <div className="relative"><Search className="absolute left-3 top-3.5 text-kMuted" size={17} /><input value={q} onChange={e => setQ(e.target.value)} className="input-k pl-10" placeholder="Search elderly member..." autoFocus /></div>
      <div className="mt-3 grid gap-2">
        {results.map(m => <button key={m.id} type="button" onClick={() => setSelected(m)} className="flex items-center justify-between rounded-xl border border-kBorder px-4 py-3 text-left hover:bg-kCream"><div><div className="text-sm font-semibold text-kInk">{m.full_name}</div><div className="text-xs text-kMuted">{m.member_id}</div></div></button>)}
        {query && results.length === 0 && <p className="text-sm text-kMuted">No matching member.</p>}
      </div>
    </div> : <form onSubmit={save} className="grid gap-4">
      <div className="rounded-xl bg-kCream p-3 text-sm"><span className="font-semibold text-kInk">{selected.full_name}</span> <span className="text-kMuted">({selected.member_id})</span> <button type="button" onClick={() => setSelected(null)} className="ml-2 text-xs font-semibold text-kOrange">Change</button></div>
      <label className="text-sm font-semibold">Reason<textarea name="reason" rows={3} className="input-k mt-2" required /></label>
      <div className="grid grid-cols-2 gap-4">
        <label className="text-sm font-semibold">Priority<select name="priority" defaultValue="Medium" className="input-k mt-2">{PRIORITIES.map(p => <option key={p}>{p}</option>)}</select></label>
        <label className="text-sm font-semibold">Due date<input name="due_date" type="date" className="input-k mt-2" /></label>
      </div>
      <label className="text-sm font-semibold">Assign to (optional)<select name="assigned_to_id" defaultValue="" className="input-k mt-2"><option value="">Unassigned</option>{assignees.map(a => <option key={a.id} value={a.id}>{a.name} ({a.role})</option>)}</select></label>
      <button disabled={saving} className="btn-orange mt-2 disabled:opacity-60">{saving ? 'Creating…' : 'Create follow-up'}</button>
    </form>}
  </Modal>
}

function EditFollowUpModal({ followup, assignees, onClose, onSaved, showToast }) {
  const [saving, setSaving] = useState(false)
  async function save(e) {
    e.preventDefault()
    const f = new FormData(e.target)
    const assignedVal = f.get('assigned_to_id')
    const data = {
      status: f.get('status'), priority: f.get('priority'),
      assigned_to_id: assignedVal ? Number(assignedVal) : null,
      due_date: f.get('due_date') || null, notes: f.get('notes') || null,
    }
    setSaving(true)
    try {
      await onSaved(followup.id, data)
      showToast('Follow-up updated')
      onClose()
    } catch (err) { showToast(errorMessage(err)) }
    finally { setSaving(false) }
  }
  return <Modal title={`${followup.elderly_member_name} — ${SOURCE_LABELS[followup.source_type]}`} onClose={onClose}>
    <div className="mb-4 rounded-xl bg-kCream p-3 text-sm text-kInk">{followup.reason}</div>
    <form onSubmit={save} className="grid gap-4">
      <div className="grid grid-cols-2 gap-4">
        <label className="text-sm font-semibold">Status<select name="status" defaultValue={followup.status} className="input-k mt-2">{STATUSES.map(s => <option key={s}>{s}</option>)}</select></label>
        <label className="text-sm font-semibold">Priority<select name="priority" defaultValue={followup.priority} className="input-k mt-2">{PRIORITIES.map(p => <option key={p}>{p}</option>)}</select></label>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <label className="text-sm font-semibold">Assign to<select name="assigned_to_id" defaultValue={followup.assigned_to_id || ''} className="input-k mt-2"><option value="">Unassigned</option>{assignees.map(a => <option key={a.id} value={a.id}>{a.name} ({a.role})</option>)}</select></label>
        <label className="text-sm font-semibold">Due date<input name="due_date" type="date" defaultValue={followup.due_date || ''} className="input-k mt-2" /></label>
      </div>
      <label className="text-sm font-semibold">Notes<textarea name="notes" defaultValue={followup.notes} rows={3} className="input-k mt-2" /></label>
      <button disabled={saving} className="btn-orange mt-2 disabled:opacity-60">{saving ? 'Saving…' : 'Save changes'}</button>
    </form>
  </Modal>
}

export default function FollowUpsManager({ showToast }) {
  const [followups, setFollowups] = useState([])
  const [assignees, setAssignees] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [statusFilter, setStatusFilter] = useState('All')
  const [overdueOnly, setOverdueOnly] = useState(false)
  const [newModalOpen, setNewModalOpen] = useState(false)
  const [editFollowup, setEditFollowup] = useState(null)

  useEffect(() => { apiFetch('/api/home-visits/assignees').then(d => setAssignees(d.assignees)).catch(() => {}) }, [])

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const params = new URLSearchParams()
      if (statusFilter !== 'All') params.set('status', statusFilter)
      if (overdueOnly) params.set('overdue', 'true')
      const data = await apiFetch(`/api/followups?${params.toString()}`)
      setFollowups(data.followups)
    } catch (err) { setError(errorMessage(err)) }
    finally { setLoading(false) }
  }, [statusFilter, overdueOnly])

  useEffect(() => { load() }, [load])

  const pendingCount = followups.filter(f => f.status !== 'Completed').length
  const overdueCount = followups.filter(f => f.is_overdue).length

  return <Shell>
    <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
      <div><div className="eyebrow">Manage</div><h1 className="font-display text-3xl font-bold text-kGreen">Follow-ups</h1></div>
      <button onClick={() => setNewModalOpen(true)} className="btn-green"><Plus size={16} /> New follow-up</button>
    </div>

    {overdueCount > 0 && <div className="mt-6 flex items-center gap-2 rounded-xl border-l-4 border-l-red-500 bg-red-50 px-5 py-3 text-sm font-semibold text-red-700 dark:bg-red-500/10"><AlertTriangle size={16} /> {overdueCount} overdue follow-up{overdueCount > 1 ? 's' : ''}</div>}

    {loading ? <LoadingState label="follow-ups" /> : error ? <ErrorState message={error} onRetry={load} /> : <div className="card-k mt-7 overflow-hidden">
      <div className="flex flex-col gap-3 border-b border-kBorderSoft p-5 sm:flex-row">
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="rounded-xl border border-kBorder bg-kSurface px-4 py-3 text-sm text-kInk"><option>All</option>{STATUSES.map(s => <option key={s}>{s}</option>)}</select>
        <label className="flex items-center gap-2 whitespace-nowrap rounded-xl border border-kBorder px-4 text-sm font-semibold text-kInk"><input type="checkbox" checked={overdueOnly} onChange={e => setOverdueOnly(e.target.checked)} className="h-4 w-4" /> Overdue only</label>
        <div className="ml-auto flex items-center text-sm text-kMuted">{pendingCount} pending</div>
      </div>
      <div className="overflow-x-auto"><table className="w-full min-w-[950px] text-left text-sm"><thead className="bg-kBorderSoft text-xs uppercase tracking-wider text-kMuted"><tr><th className="px-5 py-4">Member</th><th className="px-5 py-4">Source</th><th className="px-5 py-4">Reason</th><th className="px-5 py-4">Priority</th><th className="px-5 py-4">Assigned</th><th className="px-5 py-4">Due</th><th className="px-5 py-4">Status</th><th className="px-5 py-4">Actions</th></tr></thead><tbody>
        {followups.map(f => <tr key={f.id} className="border-b border-kBorderSoft"><td className="px-5 py-4"><div className="font-semibold text-kInk">{f.elderly_member_name}</div><div className="text-xs text-kMuted">{f.elderly_member_code}</div></td><td className="px-5 py-4 text-kMuted">{SOURCE_LABELS[f.source_type]}</td><td className="px-5 py-4 text-kMuted max-w-[220px] truncate">{f.reason}</td><td className="px-5 py-4"><StatusBadge value={f.priority} /></td><td className="px-5 py-4 text-kMuted">{f.assigned_to || 'Unassigned'}</td><td className="px-5 py-4 text-kMuted">{f.due_date ? <span className={f.is_overdue ? 'font-bold text-red-600' : ''}>{f.due_date}</span> : '—'}</td><td className="px-5 py-4"><StatusBadge value={f.status} /></td><td className="px-5 py-4"><button onClick={() => setEditFollowup(f)} className="text-kOrange"><Pencil size={16} /></button></td></tr>)}
        {followups.length === 0 && <tr><td colSpan={8} className="px-5 py-10 text-center text-sm text-kMuted">No follow-ups match your filters.</td></tr>}
      </tbody></table></div>
    </div>}

    {newModalOpen && <NewFollowUpModal assignees={assignees} onClose={() => setNewModalOpen(false)} onCreated={async data => { await apiFetch('/api/followups', { method: 'POST', body: data }); load() }} showToast={showToast} />}
    {editFollowup && <EditFollowUpModal followup={editFollowup} assignees={assignees} onClose={() => setEditFollowup(null)} onSaved={async (id, data) => { await apiFetch(`/api/followups/${id}`, { method: 'PATCH', body: data }); load() }} showToast={showToast} />}
  </Shell>
}
