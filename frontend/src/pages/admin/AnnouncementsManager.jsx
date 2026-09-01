import { useState } from 'react'
import { Megaphone, Plus } from 'lucide-react'
import Shell from '../../components/admin/Shell'
import Modal from '../../components/admin/Modal'
import StatusBadge from '../../components/admin/StatusBadge'
import { LoadingState, ErrorState, EmptyState, errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch } from '../../lib/api'
import { useApiResource } from '../../lib/useApiResource'

const AUDIENCES = ['All', 'Volunteers', 'Verified Volunteers', 'Staff', 'Admin', 'Selected']
const PRIORITIES = ['Normal', 'Important', 'Urgent']

function computedStatus(a) {
  if (!a.active) return 'Inactive'
  const now = new Date()
  if (a.publish_at && new Date(a.publish_at) > now) return 'Scheduled'
  if (a.expires_at && new Date(a.expires_at) <= now) return 'Expired'
  return 'Active'
}

function AnnouncementFormModal({ onClose, onSaved, showToast }) {
  const [audience, setAudience] = useState('All')
  const [volunteers, setVolunteers] = useState([])
  const [selectedIds, setSelectedIds] = useState([])
  const [saving, setSaving] = useState(false)

  function onAudienceChange(value) {
    setAudience(value)
    if (value === 'Selected' && volunteers.length === 0) {
      apiFetch('/api/volunteers').then(d => setVolunteers(d.volunteers)).catch(() => {})
    }
  }
  function toggleSelected(id) { setSelectedIds(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]) }

  async function save(e) {
    e.preventDefault()
    const f = new FormData(e.target)
    if (audience === 'Selected' && selectedIds.length === 0) { showToast('Choose at least one recipient'); return }
    setSaving(true)
    try {
      await apiFetch('/api/announcements', {
        method: 'POST',
        body: {
          title: f.get('title'), body: f.get('body'), priority: f.get('priority'), audience_type: audience,
          selected_user_ids: audience === 'Selected' ? selectedIds : undefined,
          publish_at: f.get('publish_at') ? new Date(f.get('publish_at')).toISOString() : null,
          expires_at: f.get('expires_at') ? new Date(f.get('expires_at')).toISOString() : null,
        },
      })
      showToast('Announcement created')
      onSaved()
      onClose()
    } catch (err) { showToast(errorMessage(err)) }
    finally { setSaving(false) }
  }

  return <Modal title="New announcement" onClose={onClose}>
    <form onSubmit={save} className="grid gap-4">
      <label className="text-sm font-semibold">Title<input name="title" className="input-k mt-2" required /></label>
      <label className="text-sm font-semibold">Body<textarea name="body" rows={4} className="input-k mt-2" required /></label>
      <div className="grid grid-cols-2 gap-4">
        <label className="text-sm font-semibold">Priority<select name="priority" defaultValue="Normal" className="input-k mt-2">{PRIORITIES.map(p => <option key={p}>{p}</option>)}</select></label>
        <label className="text-sm font-semibold">Audience<select value={audience} onChange={e => onAudienceChange(e.target.value)} className="input-k mt-2">{AUDIENCES.map(a => <option key={a}>{a}</option>)}</select></label>
      </div>
      {audience === 'Selected' && <div className="max-h-40 overflow-y-auto rounded-xl border border-kBorder p-2">
        {volunteers.length === 0 && <p className="p-2 text-xs text-kMuted">Loading volunteers…</p>}
        {volunteers.map(v => <label key={v.id} className="flex items-center gap-2 px-2 py-1.5 text-sm"><input type="checkbox" checked={selectedIds.includes(v.id)} onChange={() => toggleSelected(v.id)} className="h-4 w-4" /> {v.name}</label>)}
      </div>}
      <div className="grid grid-cols-2 gap-4">
        <label className="text-sm font-semibold">Publish at (optional)<input name="publish_at" type="datetime-local" className="input-k mt-2" /></label>
        <label className="text-sm font-semibold">Expires at (optional)<input name="expires_at" type="datetime-local" className="input-k mt-2" /></label>
      </div>
      <button disabled={saving} className="btn-orange mt-2 justify-center disabled:opacity-60">{saving ? 'Creating…' : 'Create announcement'}</button>
    </form>
  </Modal>
}

export default function AnnouncementsManager({ showToast }) {
  const api = useApiResource('/api/announcements?all=true', { listKey: 'announcements', itemKey: 'announcement' })
  const [creating, setCreating] = useState(false)

  async function toggleActive(a) {
    try { await api.patch(a.id, { active: !a.active }, '/api/announcements'); showToast(a.active ? 'Deactivated' : 'Reactivated') }
    catch (err) { showToast(errorMessage(err)) }
  }

  return <Shell>
    <div className="flex items-center justify-between">
      <div><div className="eyebrow">Communication</div><h1 className="font-display text-3xl font-bold text-kGreen">Announcements</h1></div>
      <button onClick={() => setCreating(true)} className="btn-orange"><Plus size={16} /> New announcement</button>
    </div>

    <div className="mt-7">
      {api.loading && <LoadingState label="announcements" />}
      {!api.loading && api.error && <ErrorState message={api.error} onRetry={api.reload} />}
      {!api.loading && !api.error && api.items.length === 0 && <EmptyState icon={Megaphone} title="No announcements yet" message="Create one to reach volunteers or staff." />}
      {!api.loading && !api.error && api.items.length > 0 && <div className="grid gap-3">
        {api.items.map(a => { const status = computedStatus(a); return <div key={a.id} className="card-k p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-semibold text-kInk">{a.title}</span>
                <StatusBadge value={status} />
                <StatusBadge value={a.priority} />
              </div>
              <p className="mt-1 text-sm text-kMuted">{a.body}</p>
              <div className="mt-2 text-xs text-kMuted">Audience: {a.audience_type}{a.audience_type === 'Selected' ? ` (${a.selected_user_ids?.length || 0})` : ''} &middot; By {a.created_by}</div>
            </div>
            <button onClick={() => toggleActive(a)} className="shrink-0 text-xs font-bold text-kOrange">{a.active ? 'Deactivate' : 'Reactivate'}</button>
          </div>
        </div> })}
      </div>}
    </div>

    {creating && <AnnouncementFormModal onClose={() => setCreating(false)} onSaved={api.reload} showToast={showToast} />}
  </Shell>
}
