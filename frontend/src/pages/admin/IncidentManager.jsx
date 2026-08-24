import { useState, useEffect, useCallback } from 'react'
import { Search, Plus, Pencil, AlertTriangle } from 'lucide-react'
import Shell from '../../components/admin/Shell'
import Modal from '../../components/admin/Modal'
import { LoadingState, ErrorState, errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch } from '../../lib/api'

const TYPES = ['Fall', 'Injury', 'Medical Concern', 'Accident', 'Safeguarding Concern', 'Other']
const STATUSES = ['Open', 'Under Review', 'Resolved', 'Closed']
const STATUS_STYLES = { Open: 'bg-red-100 text-red-700', 'Under Review': 'bg-kTint text-kOrange', Resolved: 'bg-kGreen/10 text-kGreen', Closed: 'bg-kBorderSoft text-kMuted' }

function fmt(iso) { return iso ? new Date(iso).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }) : '—' }

function NewIncidentModal({ onClose, onCreated, showToast }) {
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
    setSaving(true)
    try {
      await onCreated({
        elderly_member_id: selected.id,
        incident_type: f.get('incident_type'),
        occurred_at: f.get('occurred_at') ? new Date(f.get('occurred_at')).toISOString() : undefined,
        location: f.get('location') || null,
        description: f.get('description'),
        immediate_action_taken: f.get('immediate_action_taken') || null,
        emergency_contact_notified: f.get('emergency_contact_notified') === 'on',
        follow_up_required: f.get('follow_up_required') === 'on',
        follow_up_notes: f.get('follow_up_notes') || null,
      })
      showToast('Incident reported')
      onClose()
    } catch (err) { showToast(errorMessage(err)) }
    finally { setSaving(false) }
  }

  return <Modal title="Report incident" onClose={onClose}>
    {!selected ? <div>
      <div className="relative"><Search className="absolute left-3 top-3.5 text-kMuted" size={17} /><input value={q} onChange={e => setQ(e.target.value)} className="input-k pl-10" placeholder="Search elderly member..." autoFocus /></div>
      <div className="mt-3 grid gap-2">
        {results.map(m => <button key={m.id} type="button" onClick={() => setSelected(m)} className="flex items-center justify-between rounded-xl border border-kBorder px-4 py-3 text-left hover:bg-kCream"><div><div className="text-sm font-semibold text-kInk">{m.full_name}</div><div className="text-xs text-kMuted">{m.member_id}</div></div></button>)}
        {query && results.length === 0 && <p className="text-sm text-kMuted">No matching member.</p>}
      </div>
    </div> : <form onSubmit={save} className="grid gap-4">
      <div className="rounded-xl bg-kCream p-3 text-sm"><span className="font-semibold text-kInk">{selected.full_name}</span> <span className="text-kMuted">({selected.member_id})</span> <button type="button" onClick={() => setSelected(null)} className="ml-2 text-xs font-semibold text-kOrange">Change</button></div>
      <div className="grid grid-cols-2 gap-4">
        <label className="text-sm font-semibold">Type<select name="incident_type" defaultValue={TYPES[0]} className="input-k mt-2">{TYPES.map(t => <option key={t}>{t}</option>)}</select></label>
        <label className="text-sm font-semibold">When<input name="occurred_at" type="datetime-local" className="input-k mt-2" /></label>
      </div>
      <label className="text-sm font-semibold">Location<input name="location" className="input-k mt-2" /></label>
      <label className="text-sm font-semibold">What happened<textarea name="description" rows={3} className="input-k mt-2" required /></label>
      <label className="text-sm font-semibold">Immediate action taken<textarea name="immediate_action_taken" rows={2} className="input-k mt-2" /></label>
      <label className="flex items-center gap-2 text-sm font-semibold"><input name="emergency_contact_notified" type="checkbox" className="h-5 w-5" /> Emergency contact notified</label>
      <label className="flex items-center gap-2 text-sm font-semibold"><input name="follow_up_required" type="checkbox" className="h-5 w-5" /> Follow-up required</label>
      <label className="text-sm font-semibold">Follow-up notes<textarea name="follow_up_notes" rows={2} className="input-k mt-2" /></label>
      <button disabled={saving} className="btn-orange mt-2 disabled:opacity-60">{saving ? 'Reporting…' : 'Report incident'}</button>
    </form>}
  </Modal>
}

function EditIncidentModal({ incident, onClose, onSaved, showToast }) {
  const [saving, setSaving] = useState(false)
  async function save(e) {
    e.preventDefault()
    const f = new FormData(e.target)
    const data = {
      status: f.get('status'),
      resolution_notes: f.get('resolution_notes') || null,
      immediate_action_taken: f.get('immediate_action_taken') || null,
      emergency_contact_notified: f.get('emergency_contact_notified') === 'on',
      follow_up_required: f.get('follow_up_required') === 'on',
      follow_up_notes: f.get('follow_up_notes') || null,
    }
    setSaving(true)
    try {
      await onSaved(incident.id, data)
      showToast('Incident updated')
      onClose()
    } catch (err) { showToast(errorMessage(err)) }
    finally { setSaving(false) }
  }
  return <Modal title={`${incident.elderly_member_name} — ${incident.incident_type}`} onClose={onClose}>
    <div className="mb-4 rounded-xl bg-kCream p-3 text-sm text-kInk">{incident.description}</div>
    <form onSubmit={save} className="grid gap-4">
      <label className="text-sm font-semibold">Status<select name="status" defaultValue={incident.status} className="input-k mt-2">{STATUSES.map(s => <option key={s}>{s}</option>)}</select></label>
      <label className="text-sm font-semibold">Immediate action taken<textarea name="immediate_action_taken" defaultValue={incident.immediate_action_taken} rows={2} className="input-k mt-2" /></label>
      <label className="flex items-center gap-2 text-sm font-semibold"><input name="emergency_contact_notified" type="checkbox" defaultChecked={incident.emergency_contact_notified} className="h-5 w-5" /> Emergency contact notified</label>
      <label className="flex items-center gap-2 text-sm font-semibold"><input name="follow_up_required" type="checkbox" defaultChecked={incident.follow_up_required} className="h-5 w-5" /> Follow-up required</label>
      <label className="text-sm font-semibold">Follow-up notes<textarea name="follow_up_notes" defaultValue={incident.follow_up_notes} rows={2} className="input-k mt-2" /></label>
      <label className="text-sm font-semibold">Resolution notes<textarea name="resolution_notes" defaultValue={incident.resolution_notes} rows={2} className="input-k mt-2" /></label>
      <button disabled={saving} className="btn-orange mt-2 disabled:opacity-60">{saving ? 'Saving…' : 'Save changes'}</button>
    </form>
  </Modal>
}

export default function IncidentManager({ showToast }) {
  const [incidents, setIncidents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [typeFilter, setTypeFilter] = useState('All')
  const [statusFilter, setStatusFilter] = useState('All')
  const [followUpOnly, setFollowUpOnly] = useState(false)
  const [newModalOpen, setNewModalOpen] = useState(false)
  const [editIncident, setEditIncident] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const params = new URLSearchParams()
      if (typeFilter !== 'All') params.set('incident_type', typeFilter)
      if (statusFilter !== 'All') params.set('status', statusFilter)
      if (followUpOnly) params.set('follow_up_required', 'true')
      const data = await apiFetch(`/api/incidents?${params.toString()}`)
      setIncidents(data.incidents)
    } catch (err) { setError(errorMessage(err)) }
    finally { setLoading(false) }
  }, [typeFilter, statusFilter, followUpOnly])

  useEffect(() => { load() }, [load])

  const openCount = incidents.filter(i => i.status === 'Open').length

  return <Shell>
    <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
      <div><div className="eyebrow">Manage</div><h1 className="font-display text-3xl font-bold text-kGreen">Incidents</h1></div>
      <button onClick={() => setNewModalOpen(true)} className="btn-green"><Plus size={16} /> Report incident</button>
    </div>

    {openCount > 0 && <div className="mt-6 flex items-center gap-2 rounded-xl border-l-4 border-l-red-500 bg-red-50 px-5 py-3 text-sm font-semibold text-red-700 dark:bg-red-500/10"><AlertTriangle size={16} /> {openCount} open incident{openCount > 1 ? 's' : ''}</div>}

    {loading ? <LoadingState label="incidents" /> : error ? <ErrorState message={error} onRetry={load} /> : <div className="card-k mt-7 overflow-hidden">
      <div className="flex flex-col gap-3 border-b border-kBorderSoft p-5 sm:flex-row">
        <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)} className="rounded-xl border border-kBorder bg-kSurface px-4 py-3 text-sm text-kInk"><option>All</option>{TYPES.map(t => <option key={t}>{t}</option>)}</select>
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="rounded-xl border border-kBorder bg-kSurface px-4 py-3 text-sm text-kInk"><option>All</option>{STATUSES.map(s => <option key={s}>{s}</option>)}</select>
        <label className="flex items-center gap-2 whitespace-nowrap rounded-xl border border-kBorder px-4 text-sm font-semibold text-kInk"><input type="checkbox" checked={followUpOnly} onChange={e => setFollowUpOnly(e.target.checked)} className="h-4 w-4" /> Needs follow-up</label>
      </div>
      <div className="overflow-x-auto"><table className="w-full min-w-[900px] text-left text-sm"><thead className="bg-kBorderSoft text-xs uppercase tracking-wider text-kMuted"><tr><th className="px-5 py-4">Member</th><th className="px-5 py-4">Type</th><th className="px-5 py-4">When</th><th className="px-5 py-4">Status</th><th className="px-5 py-4">Follow-up</th><th className="px-5 py-4">Actions</th></tr></thead><tbody>
        {incidents.map(i => <tr key={i.id} className="border-b border-kBorderSoft"><td className="px-5 py-4"><div className="font-semibold text-kInk">{i.elderly_member_name}</div><div className="text-xs text-kMuted">{i.elderly_member_code}</div></td><td className="px-5 py-4 text-kMuted">{i.incident_type}</td><td className="px-5 py-4 text-kMuted">{fmt(i.occurred_at)}</td><td className="px-5 py-4"><span className={`rounded-full px-3 py-1 text-xs font-bold ${STATUS_STYLES[i.status]}`}>{i.status}</span></td><td className="px-5 py-4">{i.follow_up_required ? <span className="text-xs font-bold text-kOrange">Required</span> : '—'}</td><td className="px-5 py-4"><button onClick={() => setEditIncident(i)} className="text-kOrange"><Pencil size={16} /></button></td></tr>)}
        {incidents.length === 0 && <tr><td colSpan={6} className="px-5 py-10 text-center text-sm text-kMuted">No incidents match your filters.</td></tr>}
      </tbody></table></div>
    </div>}

    {newModalOpen && <NewIncidentModal onClose={() => setNewModalOpen(false)} onCreated={async data => { await apiFetch('/api/incidents', { method: 'POST', body: data }); load() }} showToast={showToast} />}
    {editIncident && <EditIncidentModal incident={editIncident} onClose={() => setEditIncident(null)} onSaved={async (id, data) => { await apiFetch(`/api/incidents/${id}`, { method: 'PATCH', body: data }); load() }} showToast={showToast} />}
  </Shell>
}
