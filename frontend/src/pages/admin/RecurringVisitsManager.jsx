import { useState, useEffect, useCallback } from 'react'
import { Search, Plus, Pencil, Repeat } from 'lucide-react'
import Shell from '../../components/admin/Shell'
import Modal from '../../components/admin/Modal'
import StatusBadge from '../../components/admin/StatusBadge'
import DataTable from '../../components/admin/DataTable'
import { errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch } from '../../lib/api'

const FREQUENCIES = ['weekly', 'biweekly', 'monthly']
const FREQUENCY_LABELS = { weekly: 'Weekly', biweekly: 'Every 2 weeks', monthly: 'Monthly' }
const PRIORITIES = ['Low', 'Medium', 'High', 'Urgent']
const STATUSES = ['Active', 'Paused', 'Cancelled']

function fmtDate(iso) { return iso ? new Date(iso + 'T00:00:00').toLocaleDateString([], { dateStyle: 'medium' }) : '—' }

function NewSeriesModal({ assignees, onClose, onCreated, showToast }) {
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
    const endDate = f.get('end_date')
    const occurrenceCount = f.get('occurrence_count')
    setSaving(true)
    try {
      await onCreated({
        elderly_member_id: selected.id,
        reason: f.get('reason'),
        priority: f.get('priority'),
        frequency: f.get('frequency'),
        start_date: f.get('start_date'),
        scheduled_time: f.get('scheduled_time'),
        end_date: endDate || null,
        occurrence_count: occurrenceCount ? Number(occurrenceCount) : null,
        assigned_to_id: assignedVal ? Number(assignedVal) : null,
      })
      showToast('Recurring series created')
      onClose()
    } catch (err) { showToast(errorMessage(err)) }
    finally { setSaving(false) }
  }

  return <Modal title="Set up recurring visits" onClose={onClose}>
    {!selected ? <div>
      <div className="relative"><Search className="absolute left-3 top-3.5 text-kMuted" size={17} /><input value={q} onChange={e => setQ(e.target.value)} className="input-k pl-10" placeholder="Search elderly member..." autoFocus /></div>
      <div className="mt-3 grid gap-2">
        {results.map(m => <button key={m.id} type="button" onClick={() => setSelected(m)} className="flex items-center justify-between rounded-xl border border-kBorder px-4 py-3 text-left hover:bg-kCream"><div><div className="text-sm font-semibold text-kInk">{m.full_name}</div><div className="text-xs text-kMuted">{m.member_id}</div></div></button>)}
        {query && results.length === 0 && <p className="text-sm text-kMuted">No matching member.</p>}
      </div>
    </div> : <form onSubmit={save} className="grid gap-4">
      <div className="rounded-xl bg-kCream p-3 text-sm"><span className="font-semibold text-kInk">{selected.full_name}</span> <span className="text-kMuted">({selected.member_id})</span> <button type="button" onClick={() => setSelected(null)} className="ml-2 text-xs font-semibold text-kOrange">Change</button></div>
      <label className="text-sm font-semibold">Reason for visits<textarea name="reason" rows={2} className="input-k mt-2" required /></label>
      <div className="grid grid-cols-2 gap-4">
        <label className="text-sm font-semibold">Frequency<select name="frequency" defaultValue="weekly" className="input-k mt-2">{FREQUENCIES.map(f => <option key={f} value={f}>{FREQUENCY_LABELS[f]}</option>)}</select></label>
        <label className="text-sm font-semibold">Priority<select name="priority" defaultValue="Medium" className="input-k mt-2">{PRIORITIES.map(p => <option key={p}>{p}</option>)}</select></label>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <label className="text-sm font-semibold">Start date<input name="start_date" type="date" className="input-k mt-2" required /></label>
        <label className="text-sm font-semibold">Time of day<input name="scheduled_time" type="time" defaultValue="09:00" className="input-k mt-2" required /></label>
      </div>
      <p className="text-xs text-kMuted -mt-2">The start date also anchors the pattern (e.g. weekly on that same weekday going forward).</p>
      <div className="grid grid-cols-2 gap-4">
        <label className="text-sm font-semibold">End date (optional)<input name="end_date" type="date" className="input-k mt-2" /></label>
        <label className="text-sm font-semibold"># of visits (optional)<input name="occurrence_count" type="number" min="1" className="input-k mt-2" placeholder="No limit" /></label>
      </div>
      <label className="text-sm font-semibold">Assign to (optional)<select name="assigned_to_id" defaultValue="" className="input-k mt-2"><option value="">Unassigned for now</option>{assignees.map(a => <option key={a.id} value={a.id}>{a.name} ({a.role})</option>)}</select></label>
      <button disabled={saving} className="btn-orange mt-2 disabled:opacity-60">{saving ? 'Creating…' : 'Create series'}</button>
    </form>}
  </Modal>
}

function EditSeriesModal({ series, assignees, onClose, onSaved, showToast }) {
  const [saving, setSaving] = useState(false)
  async function save(e) {
    e.preventDefault()
    const f = new FormData(e.target)
    const assignedVal = f.get('assigned_to_id')
    const endDate = f.get('end_date')
    const occurrenceCount = f.get('occurrence_count')
    const data = {
      assigned_to_id: assignedVal ? Number(assignedVal) : null,
      priority: f.get('priority'),
      reason: f.get('reason'),
      end_date: endDate || null,
      occurrence_count: occurrenceCount ? Number(occurrenceCount) : null,
      status: f.get('status'),
    }
    if (data.status === 'Cancelled' && series.status !== 'Cancelled') {
      if (!window.confirm('Cancel this recurring series? Any of its already-generated visits that are still upcoming and not yet completed will also be cancelled.')) { return }
    }
    setSaving(true)
    try {
      await onSaved(series.id, data)
      showToast('Recurring series updated')
      onClose()
    } catch (err) { showToast(errorMessage(err)) }
    finally { setSaving(false) }
  }
  return <Modal title={`${series.elderly_member_name} — ${FREQUENCY_LABELS[series.frequency]}`} onClose={onClose}>
    <div className="mb-4 rounded-xl bg-kCream p-3 text-sm text-kInk">
      Started {fmtDate(series.start_date)} at {series.scheduled_time} &middot; {series.occurrences_generated} visit{series.occurrences_generated === 1 ? '' : 's'} generated so far.
      <div className="mt-1 text-xs text-kMuted">Frequency and start date can't be changed here — cancel this series and create a new one if the pattern itself needs to change.</div>
    </div>
    <form onSubmit={save} className="grid gap-4">
      <label className="text-sm font-semibold">Reason<textarea name="reason" defaultValue={series.reason} rows={2} className="input-k mt-2" required /></label>
      <div className="grid grid-cols-2 gap-4">
        <label className="text-sm font-semibold">Priority<select name="priority" defaultValue={series.priority} className="input-k mt-2">{PRIORITIES.map(p => <option key={p}>{p}</option>)}</select></label>
        <label className="text-sm font-semibold">Status<select name="status" defaultValue={series.status} className="input-k mt-2">{STATUSES.map(s => <option key={s}>{s}</option>)}</select></label>
      </div>
      <label className="text-sm font-semibold">Assign to<select name="assigned_to_id" defaultValue={series.assigned_to_id || ''} className="input-k mt-2"><option value="">Unassigned</option>{assignees.map(a => <option key={a.id} value={a.id}>{a.name} ({a.role})</option>)}</select></label>
      <div className="grid grid-cols-2 gap-4">
        <label className="text-sm font-semibold">End date<input name="end_date" type="date" defaultValue={series.end_date || ''} className="input-k mt-2" /></label>
        <label className="text-sm font-semibold"># of visits<input name="occurrence_count" type="number" min="1" defaultValue={series.occurrence_count || ''} className="input-k mt-2" placeholder="No limit" /></label>
      </div>
      <button disabled={saving} className="btn-orange mt-2 disabled:opacity-60">{saving ? 'Saving…' : 'Save changes'}</button>
    </form>
  </Modal>
}

export default function RecurringVisitsManager({ showToast }) {
  const [series, setSeries] = useState([])
  const [assignees, setAssignees] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [statusFilter, setStatusFilter] = useState('All')
  const [newModalOpen, setNewModalOpen] = useState(false)
  const [editSeries, setEditSeries] = useState(null)

  useEffect(() => { apiFetch('/api/home-visits/assignees').then(d => setAssignees(d.assignees)).catch(() => {}) }, [])

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const params = new URLSearchParams()
      if (statusFilter !== 'All') params.set('status', statusFilter)
      const data = await apiFetch(`/api/recurring-visits?${params.toString()}`)
      setSeries(data.series)
    } catch (err) { setError(errorMessage(err)) }
    finally { setLoading(false) }
  }, [statusFilter])

  useEffect(() => { load() }, [load])

  const columns = [
    { key: 'elderly_member_name', label: 'Member', sortable: true, render: s => <><div className="font-semibold text-kInk">{s.elderly_member_name}</div><div className="text-xs text-kMuted">{s.elderly_member_code}</div></> },
    { key: 'frequency', label: 'Frequency', sortable: true, render: s => <span className="flex items-center gap-1.5 text-kMuted"><Repeat size={13} /> {FREQUENCY_LABELS[s.frequency]}</span> },
    { key: 'start_date', label: 'Start', sortable: true, render: s => <span className="text-kMuted">{fmtDate(s.start_date)} &middot; {s.scheduled_time}</span> },
    { key: 'end_date', label: 'Ends', render: s => <span className="text-kMuted">{s.end_date ? fmtDate(s.end_date) : s.occurrence_count ? `After ${s.occurrence_count} visits` : 'No end date'}</span> },
    { key: 'assigned_to', label: 'Assigned to', sortable: true, render: s => <span className="text-kMuted">{s.assigned_to || 'Unassigned'}</span> },
    { key: 'visit_count', label: 'Generated', sortable: true, align: 'right', render: s => <span className="font-semibold text-kInk">{s.visit_count}</span> },
    { key: 'status', label: 'Status', sortable: true, render: s => <StatusBadge value={s.status} /> },
    { key: 'actions', label: 'Actions', render: s => <button onClick={() => setEditSeries(s)} className="text-kOrange"><Pencil size={16} /></button> },
  ]

  return <Shell>
    <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
      <div><div className="eyebrow">Schedule</div><h1 className="font-display text-3xl font-bold text-kGreen">Recurring visits</h1></div>
      <button onClick={() => setNewModalOpen(true)} className="btn-green"><Plus size={16} /> Set up recurring visits</button>
    </div>

    <div className="mt-7">
      <DataTable
        columns={columns}
        data={series}
        loading={loading}
        error={error}
        onRetry={load}
        emptyMessage="No recurring visit series yet."
        minWidth={950}
        header={<>
          <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="rounded-xl border border-kBorder bg-kSurface px-4 py-3 text-sm text-kInk"><option>All</option>{STATUSES.map(s => <option key={s}>{s}</option>)}</select>
        </>}
      />
    </div>

    {newModalOpen && <NewSeriesModal assignees={assignees} onClose={() => setNewModalOpen(false)} onCreated={async data => { await apiFetch('/api/recurring-visits', { method: 'POST', body: data }); load() }} showToast={showToast} />}
    {editSeries && <EditSeriesModal series={editSeries} assignees={assignees} onClose={() => setEditSeries(null)} onSaved={async (id, data) => { await apiFetch(`/api/recurring-visits/${id}`, { method: 'PATCH', body: data }); load() }} showToast={showToast} />}
  </Shell>
}
