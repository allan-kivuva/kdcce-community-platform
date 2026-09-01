import { useState, useEffect, useCallback } from 'react'
import { FileText, Home, Plus, Upload, Users } from 'lucide-react'
import Shell from '../../components/admin/Shell'
import Modal from '../../components/admin/Modal'
import StatusBadge from '../../components/admin/StatusBadge'
import { LoadingState, ErrorState, EmptyState, errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch, uploadForm } from '../../lib/api'

const STATUSES = ['Draft', 'Active', 'Paused', 'Completed', 'Archived']
const CATEGORIES = ['Program Guide', 'Volunteer Instructions', 'Policy', 'Event Material', 'Training Reference', 'Form', 'Other']

function fmtDate(d) { return d ? new Date(d).toLocaleDateString([], { dateStyle: 'medium' }) : '—' }

function ProgramFormModal({ program, onClose, onSaved, showToast }) {
  const [saving, setSaving] = useState(false)
  const [staff, setStaff] = useState([])
  const isEdit = !!program

  useEffect(() => {
    apiFetch('/api/home-visits/assignees').then(d => setStaff(d.assignees.filter(a => a.role !== 'volunteer'))).catch(() => {})
  }, [])

  async function save(e) {
    e.preventDefault()
    const f = new FormData(e.target)
    setSaving(true)
    try {
      const body = {
        name: f.get('name'), category: f.get('category') || null, status: f.get('status'),
        description: f.get('description') || null, location: f.get('location') || null,
        target_population: f.get('target_population') || null, goals: f.get('goals') || null,
        coordinator_id: f.get('coordinator_id') ? Number(f.get('coordinator_id')) : null,
        start_date: f.get('start_date') || null, end_date: f.get('end_date') || null,
      }
      if (isEdit) await apiFetch(`/api/programs/${program.id}`, { method: 'PATCH', body })
      else await apiFetch('/api/programs', { method: 'POST', body })
      showToast(isEdit ? 'Program updated' : 'Program created')
      onSaved()
      onClose()
    } catch (err) { showToast(errorMessage(err)) }
    finally { setSaving(false) }
  }

  return <Modal title={isEdit ? 'Edit program' : 'New program'} onClose={onClose} wide>
    <form onSubmit={save} className="grid gap-4">
      <label className="text-sm font-semibold">Name<input name="name" defaultValue={program?.name} className="input-k mt-2" required /></label>
      <div className="grid grid-cols-2 gap-4">
        <label className="text-sm font-semibold">Category<input name="category" defaultValue={program?.category} className="input-k mt-2" placeholder="e.g. Nutrition" /></label>
        <label className="text-sm font-semibold">Status<select name="status" defaultValue={program?.status || 'Draft'} className="input-k mt-2">{STATUSES.map(s => <option key={s}>{s}</option>)}</select></label>
      </div>
      <label className="text-sm font-semibold">Description<textarea name="description" defaultValue={program?.description} rows={2} className="input-k mt-2" /></label>
      <label className="text-sm font-semibold">Goals / objectives<textarea name="goals" defaultValue={program?.goals} rows={2} className="input-k mt-2" /></label>
      <div className="grid grid-cols-2 gap-4">
        <label className="text-sm font-semibold">Coordinator<select name="coordinator_id" defaultValue={program?.coordinator_id || ''} className="input-k mt-2"><option value="">Unassigned</option>{staff.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}</select></label>
        <label className="text-sm font-semibold">Location<input name="location" defaultValue={program?.location} className="input-k mt-2" /></label>
      </div>
      <label className="text-sm font-semibold">Target population<input name="target_population" defaultValue={program?.target_population} className="input-k mt-2" placeholder="e.g. Elderly residents in Kibera" /></label>
      <div className="grid grid-cols-2 gap-4">
        <label className="text-sm font-semibold">Start date<input name="start_date" type="date" defaultValue={program?.start_date} className="input-k mt-2" /></label>
        <label className="text-sm font-semibold">End date<input name="end_date" type="date" defaultValue={program?.end_date} className="input-k mt-2" /></label>
      </div>
      <button disabled={saving} className="btn-orange mt-2 disabled:opacity-60">{saving ? 'Saving…' : isEdit ? 'Save changes' : 'Create program'}</button>
    </form>
  </Modal>
}

function AnalyticsTab({ programId, showToast }) {
  const [data, setData] = useState(null)
  useEffect(() => { apiFetch(`/api/programs/${programId}/analytics`).then(d => setData(d.analytics)).catch(err => showToast(errorMessage(err))) }, [programId, showToast])
  if (!data) return <p className="text-sm text-kMuted">Loading…</p>
  const cards = [
    ['Activities', data.activities_count], ['Upcoming', data.upcoming_activities], ['Completed', data.completed_activities],
    ['Elderly served', data.elderly_participants_served], ['Repeat participants', data.repeat_participants],
    ['Total attendance', data.total_event_attendance], ['Volunteers involved', data.volunteer_participation],
    ['Attendance rate', data.attendance_rate === null ? '—' : `${data.attendance_rate}%`],
  ]
  return <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
    {cards.map(([label, value]) => <div key={label} className="card-k p-4 text-center"><div className="font-display text-2xl font-bold text-kGreen">{value}</div><div className="text-xs text-kMuted">{label}</div></div>)}
  </div>
}

function ActivitiesTab({ programId }) {
  const [activities, setActivities] = useState(null)
  useEffect(() => { apiFetch(`/api/activities?program_id=${programId}`).then(d => setActivities(d.activities)).catch(() => setActivities([])) }, [programId])
  if (!activities) return <p className="text-sm text-kMuted">Loading…</p>
  const now = new Date()
  const upcoming = activities.filter(a => new Date(a.scheduled_at) > now)
  const past = activities.filter(a => new Date(a.scheduled_at) <= now)
  return <div className="grid gap-5">
    {[['Upcoming', upcoming], ['Past', past]].map(([label, list]) => <div key={label}>
      <div className="text-xs font-bold uppercase tracking-wide text-kMuted">{label} ({list.length})</div>
      <div className="mt-2 grid gap-2">
        {list.map(a => <div key={a.id} className="flex items-center justify-between rounded-xl bg-kCream px-3 py-2.5">
          <div><div className="text-sm font-semibold text-kInk">{a.title}</div><div className="text-xs text-kMuted">{new Date(a.scheduled_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })} &middot; {a.participant_count} participants &middot; {a.confirmed_volunteer_count ?? 0} volunteers</div></div>
          <StatusBadge value={a.status} />
        </div>)}
        {list.length === 0 && <p className="text-sm text-kMuted">None.</p>}
      </div>
    </div>)}
  </div>
}

function ResourcesTab({ programId, showToast }) {
  const [resources, setResources] = useState(null)
  const [uploading, setUploading] = useState(false)
  const load = useCallback(() => { apiFetch(`/api/resources?program_id=${programId}`).then(d => setResources(d.resources)).catch(err => showToast(errorMessage(err))) }, [programId, showToast])
  useEffect(() => { load() }, [load])

  async function upload(e) {
    e.preventDefault()
    const f = new FormData(e.target)
    f.set('program_id', programId)
    if (!f.get('file') || !f.get('file').name) { showToast('Choose a file first'); return }
    setUploading(true)
    try { await uploadForm('/api/resources', f); showToast('Resource uploaded'); e.target.reset(); load() }
    catch (err) { showToast(errorMessage(err)) }
    finally { setUploading(false) }
  }

  async function remove(id) {
    if (!window.confirm('Delete this resource?')) return
    try { await apiFetch(`/api/resources/${id}`, { method: 'DELETE' }); load() }
    catch (err) { showToast(errorMessage(err)) }
  }

  if (!resources) return <p className="text-sm text-kMuted">Loading…</p>
  return <div className="grid gap-5">
    <form onSubmit={upload} className="grid gap-3 rounded-xl bg-kCream p-4">
      <div className="grid grid-cols-2 gap-3">
        <input name="title" placeholder="Title" className="input-k" required />
        <select name="category" defaultValue="Program Guide" className="input-k">{CATEGORIES.map(c => <option key={c}>{c}</option>)}</select>
      </div>
      <select name="visibility" defaultValue="Volunteers" className="input-k"><option value="Volunteers">Visible to volunteers</option><option value="Admin">Admin/staff only</option></select>
      <input name="file" type="file" accept="image/jpeg,image/png,image/webp,application/pdf" className="text-sm" required />
      <button disabled={uploading} className="btn-orange w-fit disabled:opacity-60"><Upload size={14} /> {uploading ? 'Uploading…' : 'Upload resource'}</button>
    </form>
    <div className="grid gap-2">
      {resources.map(r => <div key={r.id} className="flex items-center justify-between rounded-xl bg-kCream px-3 py-2.5">
        <div className="flex items-center gap-2"><FileText size={15} className="text-kOrange" /><div><div className="text-sm font-semibold text-kInk">{r.title}</div><div className="text-xs text-kMuted">{r.document_type} &middot; {r.visibility}</div></div></div>
        <button onClick={() => remove(r.id)} className="text-xs font-bold text-red-500">Delete</button>
      </div>)}
      {resources.length === 0 && <p className="text-sm text-kMuted">No resources uploaded yet.</p>}
    </div>
  </div>
}

function ProgramDetailModal({ program, onClose, showToast }) {
  const [tab, setTab] = useState('overview')
  return <Modal title="Program details" onClose={onClose} wide>
    <div className="-mt-2 mb-4">
      <div className="font-display text-lg font-bold text-kGreen">{program.name}</div>
      <div className="mt-1 flex flex-wrap items-center gap-2"><StatusBadge value={program.status} />{program.category && <span className="text-xs text-kMuted">{program.category}</span>}</div>
    </div>
    <div className="flex gap-1 overflow-x-auto border-b border-kBorderSoft pb-2">
      {['overview', 'activities', 'resources', 'analytics'].map(t => <button key={t} onClick={() => setTab(t)} className={`shrink-0 rounded-lg px-3 py-1.5 text-sm font-semibold capitalize ${tab === t ? 'bg-kOrange text-white' : 'text-kMuted hover:bg-kCream'}`}>{t}</button>)}
    </div>
    <div className="mt-4">
      {tab === 'overview' && <div className="grid gap-3 text-sm">
        {program.description && <p className="text-kInk">{program.description}</p>}
        {program.goals && <div><div className="text-xs font-bold uppercase text-kMuted">Goals</div><p className="mt-1 text-kInk">{program.goals}</p></div>}
        <div className="grid grid-cols-2 gap-3 text-xs text-kMuted">
          <div><span className="font-bold">Coordinator:</span> {program.coordinator || '—'}</div>
          <div><span className="font-bold">Location:</span> {program.location || '—'}</div>
          <div><span className="font-bold">Target population:</span> {program.target_population || '—'}</div>
          <div><span className="font-bold">Dates:</span> {fmtDate(program.start_date)} – {fmtDate(program.end_date)}</div>
        </div>
      </div>}
      {tab === 'activities' && <ActivitiesTab programId={program.id} />}
      {tab === 'resources' && <ResourcesTab programId={program.id} showToast={showToast} />}
      {tab === 'analytics' && <AnalyticsTab programId={program.id} showToast={showToast} />}
    </div>
  </Modal>
}

export default function ProgramsManager({ showToast }) {
  const [programs, setPrograms] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [formOpen, setFormOpen] = useState(null)
  const [viewing, setViewing] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try { setPrograms((await apiFetch('/api/programs')).programs) }
    catch (err) { setError(errorMessage(err)) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  return <Shell>
    <div className="flex items-center justify-between">
      <div><div className="eyebrow">Manage</div><h1 className="font-display text-3xl font-bold text-kGreen">Programs</h1></div>
      <button onClick={() => setFormOpen('create')} className="btn-orange"><Plus size={16} /> New program</button>
    </div>

    <div className="mt-7">
      {loading && <LoadingState label="programs" />}
      {!loading && error && <ErrorState message={error} onRetry={load} />}
      {!loading && !error && programs.length === 0 && <EmptyState icon={Home} title="No programs yet" message="Create your first program to start grouping activities." />}
      {!loading && !error && programs.length > 0 && <div className="grid gap-3">
        {programs.map(p => <div key={p.id} className="card-k flex flex-wrap items-center justify-between gap-3 p-5">
          <div className="flex items-center gap-3">
            <div className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-kTint text-kOrange"><Home size={18} /></div>
            <div>
              <div className="flex items-center gap-2"><span className="font-semibold text-kInk">{p.name}</span><StatusBadge value={p.status} /></div>
              <div className="mt-0.5 text-xs text-kMuted">{p.category || 'Uncategorized'} &middot; {p.coordinator || 'No coordinator'} &middot; <span className="inline-flex items-center gap-1"><Users size={11} /> {p.activity_count} activities</span></div>
            </div>
          </div>
          <div className="flex shrink-0 gap-3">
            <button onClick={() => setViewing(p)} className="text-xs font-bold text-kOrange">View</button>
            <button onClick={() => setFormOpen(p)} className="text-xs font-bold text-kMuted">Edit</button>
          </div>
        </div>)}
      </div>}
    </div>

    {formOpen && <ProgramFormModal program={formOpen === 'create' ? null : formOpen} onClose={() => setFormOpen(null)} onSaved={load} showToast={showToast} />}
    {viewing && <ProgramDetailModal program={viewing} onClose={() => setViewing(null)} showToast={showToast} />}
  </Shell>
}
