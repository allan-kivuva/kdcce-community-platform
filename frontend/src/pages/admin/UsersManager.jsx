import { useState } from 'react'
import { ChevronDown, Plus, RotateCcw, ShieldAlert } from 'lucide-react'
import Shell from '../../components/admin/Shell'
import Modal from '../../components/admin/Modal'
import StatusBadge from '../../components/admin/StatusBadge'
import DataTable from '../../components/admin/DataTable'
import { errorMessage, timeAgo } from '../../components/admin/adminHelpers'
import { apiFetch, getStoredUser } from '../../lib/api'
import { useApiResource } from '../../lib/useApiResource'

const ROLES = ['admin', 'staff', 'volunteer']
const ROLE_STYLES = { admin: 'bg-purple-500/15 text-purple-500', staff: 'bg-blue-500/15 text-blue-500', volunteer: 'bg-slate-500/15 text-slate-500' }

function RoleBadge({ role }) {
  return <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-bold capitalize ${ROLE_STYLES[role] || ''}`}>{role}</span>
}

function CreateUserModal({ onClose, onSaved, showToast }) {
  const [saving, setSaving] = useState(false)

  async function save(e) {
    e.preventDefault()
    const f = new FormData(e.target)
    setSaving(true)
    try {
      await apiFetch('/api/users', { method: 'POST', body: { name: f.get('name'), email: f.get('email'), password: f.get('password'), role: f.get('role') } })
      showToast('User created')
      onSaved()
      onClose()
    } catch (err) { showToast(errorMessage(err)) }
    finally { setSaving(false) }
  }

  return <Modal title="New user" onClose={onClose}>
    <form onSubmit={save} className="grid gap-4">
      <label className="text-sm font-semibold">Name<input name="name" className="input-k mt-2" required /></label>
      <label className="text-sm font-semibold">Email<input name="email" type="email" className="input-k mt-2" required /></label>
      <label className="text-sm font-semibold">Temporary password<input name="password" type="text" minLength={8} className="input-k mt-2" required /></label>
      <label className="text-sm font-semibold">Role<select name="role" className="input-k mt-2" defaultValue="staff">{ROLES.map(r => <option key={r} value={r}>{r}</option>)}</select></label>
      <button disabled={saving} className="btn-orange mt-2 disabled:opacity-60">{saving ? 'Creating…' : 'Create user'}</button>
    </form>
  </Modal>
}

function UserActionsMenu({ user, currentUserId, onChanged, showToast }) {
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const isSelf = user.id === currentUserId

  async function run(action) {
    setBusy(true)
    setOpen(false)
    try {
      if (action === 'promote') await apiFetch(`/api/users/${user.id}/role`, { method: 'PATCH', body: { role: 'admin' } })
      else if (action === 'demote-staff') await apiFetch(`/api/users/${user.id}/role`, { method: 'PATCH', body: { role: 'staff' } })
      else if (action === 'activate') await apiFetch(`/api/users/${user.id}/status`, { method: 'PATCH', body: { active: true } })
      else if (action === 'deactivate') await apiFetch(`/api/users/${user.id}/status`, { method: 'PATCH', body: { active: false } })
      else if (action === 'restore') await apiFetch(`/api/users/${user.id}/restore`, { method: 'POST' })
      else if (action === 'delete') {
        if (!window.confirm(`Remove ${user.name}'s account? This can be restored later.`)) { setBusy(false); return }
        await apiFetch(`/api/users/${user.id}`, { method: 'DELETE' })
      } else if (action === 'reset-password') {
        const res = await apiFetch(`/api/users/${user.id}/reset-password`, { method: 'POST' })
        window.prompt('Temporary password (copy it now — it will not be shown again):', res.temporary_password)
      }
      onChanged()
    } catch (err) { showToast(errorMessage(err)) }
    finally { setBusy(false) }
  }

  return <div className="relative inline-block text-left" onClick={e => e.stopPropagation()}>
    <button disabled={busy} onClick={() => setOpen(o => !o)} className="flex items-center gap-1 rounded-lg border border-kBorderSoft px-2.5 py-1.5 text-xs font-bold text-kInk hover:bg-kTint disabled:opacity-60">
      Actions <ChevronDown size={12} />
    </button>
    {open && <div className="absolute right-0 z-30 mt-1 w-52 overflow-hidden rounded-xl border border-kBorderSoft bg-kSurface py-1 text-sm shadow-soft dark:shadow-none">
      {user.deleted_at ? (
        <button onClick={() => run('restore')} className="flex w-full items-center gap-2 px-3 py-2 text-left font-semibold hover:bg-kTint"><RotateCcw size={14} /> Restore account</button>
      ) : <>
        {user.role !== 'admin' && <button onClick={() => run('promote')} className="w-full px-3 py-2 text-left font-semibold hover:bg-kTint">Promote to admin</button>}
        {user.role === 'admin' && !isSelf && <button onClick={() => run('demote-staff')} className="w-full px-3 py-2 text-left font-semibold hover:bg-kTint">Demote to staff</button>}
        {user.active
          ? <button onClick={() => run('deactivate')} className="w-full px-3 py-2 text-left font-semibold text-amber-600 hover:bg-kTint">Deactivate</button>
          : <button onClick={() => run('activate')} className="w-full px-3 py-2 text-left font-semibold hover:bg-kTint">Activate</button>}
        <button onClick={() => run('reset-password')} className="w-full px-3 py-2 text-left font-semibold hover:bg-kTint">Reset password</button>
        <button onClick={() => run('delete')} className="w-full px-3 py-2 text-left font-semibold text-red-500 hover:bg-kTint">Remove account</button>
      </>}
    </div>}
  </div>
}

export default function UsersManager({ showToast }) {
  const currentUser = getStoredUser()
  const [role, setRole] = useState('')
  const [status, setStatus] = useState('')
  const [q, setQ] = useState('')
  const [includeDeleted, setIncludeDeleted] = useState(false)
  const [formOpen, setFormOpen] = useState(false)

  const params = new URLSearchParams()
  if (role) params.set('role', role)
  if (status) params.set('active', status)
  if (q) params.set('q', q)
  if (includeDeleted) params.set('include_deleted', 'true')
  params.set('per_page', '100')
  const path = `/api/users?${params.toString()}`
  const usersApi = useApiResource(path, { listKey: 'users', itemKey: 'user' })

  const columns = [
    {
      key: 'name', label: 'User', sortable: true,
      render: u => <div>
        <div className="font-semibold text-kInk">{u.name}{u.deleted_at && <span className="ml-2 text-xs font-normal text-red-500">Removed</span>}</div>
        <div className="text-xs text-kMuted">{u.email}</div>
      </div>,
    },
    { key: 'role', label: 'Role', sortable: true, render: u => <RoleBadge role={u.role} /> },
    { key: 'active', label: 'Status', sortable: true, render: u => <StatusBadge value={u.active ? 'Active' : 'Inactive'} /> },
    { key: 'volunteer_status', label: 'Volunteer status', render: u => <StatusBadge value={u.volunteer_status} /> },
    { key: 'two_factor_enabled', label: '2FA', render: u => u.two_factor_enabled ? <span className="text-xs font-bold text-emerald-500">On</span> : <span className="text-xs text-kMuted">Off</span> },
    { key: 'last_login_at', label: 'Last login', sortable: true, render: u => u.last_login_at ? timeAgo(u.last_login_at) : 'Never' },
    { key: 'created_at', label: 'Joined', sortable: true, render: u => new Date(u.created_at).toLocaleDateString([], { dateStyle: 'medium' }) },
    { key: 'actions', label: '', align: 'right', render: u => <UserActionsMenu user={u} currentUserId={currentUser?.id} onChanged={usersApi.reload} showToast={showToast} /> },
  ]

  return <Shell>
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div><div className="eyebrow">Administration</div><h1 className="font-display text-3xl font-bold text-kGreen">Users</h1></div>
      <button onClick={() => setFormOpen(true)} className="btn-orange"><Plus size={16} /> New user</button>
    </div>

    <div className="mt-6 flex flex-wrap items-center gap-3">
      <input value={q} onChange={e => setQ(e.target.value)} placeholder="Search name or email…" className="input-k w-64" />
      <select value={role} onChange={e => setRole(e.target.value)} className="input-k w-40"><option value="">All roles</option>{ROLES.map(r => <option key={r} value={r}>{r}</option>)}</select>
      <select value={status} onChange={e => setStatus(e.target.value)} className="input-k w-40">
        <option value="">All statuses</option><option value="true">Active</option><option value="false">Inactive</option>
      </select>
      <label className="flex items-center gap-2 text-sm font-semibold text-kMuted"><input type="checkbox" checked={includeDeleted} onChange={e => setIncludeDeleted(e.target.checked)} /> Include removed</label>
    </div>

    <div className="mt-4">
      <DataTable
        columns={columns}
        data={usersApi.items}
        loading={usersApi.loading}
        error={usersApi.error}
        onRetry={usersApi.reload}
        emptyMessage="No users match these filters."
        minWidth={900}
      />
    </div>
    {usersApi.items.some(u => !u.active && !u.deleted_at) && (
      <div className="mt-4 flex items-center gap-2 rounded-xl bg-amber-500/10 px-4 py-3 text-xs font-semibold text-amber-600"><ShieldAlert size={14} /> Some accounts are deactivated — a disabled account cannot sign in even with a still-valid session token.</div>
    )}

    {formOpen && <CreateUserModal onClose={() => setFormOpen(false)} onSaved={usersApi.reload} showToast={showToast} />}
  </Shell>
}
