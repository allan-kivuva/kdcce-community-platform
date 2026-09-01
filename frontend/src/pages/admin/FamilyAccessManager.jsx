import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus } from 'lucide-react'
import Shell from '../../components/admin/Shell'
import Modal from '../../components/admin/Modal'
import StatusBadge from '../../components/admin/StatusBadge'
import DataTable from '../../components/admin/DataTable'
import { errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch } from '../../lib/api'
import { useApiResource } from '../../lib/useApiResource'

function NewRelationshipModal({ familyUsers, members, onClose, onSaved, showToast }) {
  const [saving, setSaving] = useState(false)

  async function save(e) {
    e.preventDefault()
    const f = new FormData(e.target)
    setSaving(true)
    try {
      await apiFetch('/api/admin/family-access', {
        method: 'POST',
        body: {
          user_id: Number(f.get('user_id')),
          elderly_member_id: Number(f.get('elderly_member_id')),
          relationship: f.get('relationship'),
        },
      })
      showToast('Relationship created as Pending')
      onSaved()
      onClose()
    } catch (err) { showToast(errorMessage(err)) }
    finally { setSaving(false) }
  }

  return <Modal title="New family relationship" onClose={onClose}>
    <form onSubmit={save} className="grid gap-4">
      <label className="text-sm font-semibold">Family account
        <select name="user_id" className="input-k mt-2" required>
          <option value="">Select a family account…</option>
          {familyUsers.map(u => <option key={u.id} value={u.id}>{u.name} ({u.email})</option>)}
        </select>
      </label>
      <label className="text-sm font-semibold">Elderly member
        <select name="elderly_member_id" className="input-k mt-2" required>
          <option value="">Select a member…</option>
          {members.map(m => <option key={m.id} value={m.id}>{m.full_name} ({m.member_id})</option>)}
        </select>
      </label>
      <label className="text-sm font-semibold">Relationship<input name="relationship" placeholder="e.g. Daughter, Son, Guardian" className="input-k mt-2" required /></label>
      <button disabled={saving} className="btn-orange mt-2 disabled:opacity-60">{saving ? 'Creating…' : 'Create relationship'}</button>
    </form>
  </Modal>
}

function ActionsCell({ access, onChanged, showToast }) {
  const [busy, setBusy] = useState(false)

  async function run(action) {
    setBusy(true)
    try {
      await apiFetch(`/api/admin/family-access/${access.id}/${action}`, { method: 'PATCH' })
      showToast(`Relationship ${action}d`)
      onChanged()
    } catch (err) { showToast(errorMessage(err)) }
    finally { setBusy(false) }
  }

  const status = access.access_status
  return <div className="flex justify-end gap-2">
    {(status === 'Pending' || status === 'Suspended') && <button disabled={busy} onClick={() => run('approve')} className="text-xs font-bold text-emerald-600 disabled:opacity-60">Approve</button>}
    {status === 'Active' && <button disabled={busy} onClick={() => run('suspend')} className="text-xs font-bold text-amber-600 disabled:opacity-60">Suspend</button>}
    {status !== 'Revoked' && <button disabled={busy} onClick={() => run('revoke')} className="text-xs font-bold text-red-500 disabled:opacity-60">Revoke</button>}
  </div>
}

export default function FamilyAccessManager({ showToast }) {
  const [familyUsers, setFamilyUsers] = useState([])
  const [members, setMembers] = useState([])
  const [memberFilter, setMemberFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [formOpen, setFormOpen] = useState(false)

  useEffect(() => {
    apiFetch('/api/users?role=family&per_page=100').then(d => setFamilyUsers(d.users)).catch(() => {})
    apiFetch('/api/elderly').then(d => setMembers(d.members)).catch(() => {})
  }, [])

  const params = new URLSearchParams()
  if (memberFilter) params.set('elderly_member_id', memberFilter)
  if (statusFilter) params.set('access_status', statusFilter)
  const path = `/api/admin/family-access?${params.toString()}`
  const accessApi = useApiResource(path, { listKey: 'family_access', itemKey: 'access' })

  const columns = [
    {
      key: 'user_name', label: 'Family account', sortable: true,
      render: a => <div><div className="font-semibold text-kInk">{a.user_name}</div><div className="text-xs text-kMuted">{a.user_email}</div></div>,
    },
    { key: 'elderly_member_name', label: 'Member', sortable: true },
    { key: 'relationship', label: 'Relationship' },
    { key: 'access_status', label: 'Status', sortable: true, render: a => <StatusBadge value={a.access_status} /> },
    { key: 'approved_by', label: 'Approved by', render: a => a.approved_by ? `${a.approved_by}${a.approved_at ? ' · ' + new Date(a.approved_at).toLocaleDateString() : ''}` : '—' },
    { key: 'actions', label: '', align: 'right', render: a => <ActionsCell access={a} onChanged={accessApi.reload} showToast={showToast} /> },
  ]

  return <Shell>
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div><div className="eyebrow">Family Portal</div><h1 className="font-display text-3xl font-bold text-kGreen">Family Access</h1></div>
      <button onClick={() => setFormOpen(true)} className="btn-orange"><Plus size={16} /> New relationship</button>
    </div>
    <p className="mt-2 max-w-2xl text-sm text-kMuted">
      Link a family-role account to an elderly member's record. The family account itself must already exist — create it first from <Link to="/admin/users" className="font-bold text-kOrange">Users</Link>.
    </p>

    <div className="mt-6 flex flex-wrap items-center gap-3">
      <select value={memberFilter} onChange={e => setMemberFilter(e.target.value)} className="input-k w-56">
        <option value="">All members</option>
        {members.map(m => <option key={m.id} value={m.id}>{m.full_name}</option>)}
      </select>
      <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="input-k w-48">
        <option value="">All statuses</option>
        <option>Pending</option><option>Active</option><option>Suspended</option><option>Revoked</option>
      </select>
    </div>

    <div className="mt-4">
      <DataTable
        columns={columns}
        data={accessApi.items}
        loading={accessApi.loading}
        error={accessApi.error}
        onRetry={accessApi.reload}
        emptyMessage="No family relationships recorded yet."
        minWidth={850}
      />
    </div>

    {formOpen && <NewRelationshipModal familyUsers={familyUsers} members={members} onClose={() => setFormOpen(false)} onSaved={accessApi.reload} showToast={showToast} />}
  </Shell>
}
