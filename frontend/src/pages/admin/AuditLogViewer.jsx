import { useState } from 'react'
import { History } from 'lucide-react'
import Shell from '../../components/admin/Shell'
import Modal from '../../components/admin/Modal'
import DataTable from '../../components/admin/DataTable'
import { useApiResource } from '../../lib/useApiResource'

const ACTIONS = [
  'create', 'update', 'delete', 'restore', 'role_change', 'activate', 'deactivate',
  'verify', 'reject', 'reset_password', 'enable', 'disable', 'revoke', 'revoke_others',
  'revoke_all', 'recovery_code_used', 'link_donations', 'status_change',
]
const RESOURCE_TYPES = [
  'user', 'session', 'two_factor', 'volunteer_profile', 'elderly_member', 'incident',
  'home_visit', 'assistance_request', 'document', 'training_course', 'donor', 'campaign',
  'expense', 'budget', 'donation',
]

function DiffBlock({ label, data }) {
  return <div>
    <div className="text-xs font-bold uppercase tracking-wide text-kMuted">{label}</div>
    {data ? (
      <pre className="mt-2 overflow-x-auto rounded-xl bg-kCream p-3 text-xs text-kInk">{JSON.stringify(data, null, 2)}</pre>
    ) : <p className="mt-2 text-sm text-kMuted">—</p>}
  </div>
}

function AuditDetailModal({ entry, onClose }) {
  return <Modal title="Audit log entry" onClose={onClose} wide>
    <div className="-mt-2 mb-4 grid gap-1 text-sm">
      <div><span className="font-semibold text-kInk">Actor:</span> {entry.actor}</div>
      <div><span className="font-semibold text-kInk">Action:</span> {entry.action}</div>
      <div><span className="font-semibold text-kInk">Resource:</span> {entry.resource_type} #{entry.resource_id}</div>
      <div><span className="font-semibold text-kInk">When:</span> {new Date(entry.created_at).toLocaleString()}</div>
    </div>
    <div className="grid gap-4 sm:grid-cols-2">
      <DiffBlock label="Before" data={entry.before} />
      <DiffBlock label="After" data={entry.after} />
    </div>
  </Modal>
}

export default function AuditLogViewer({ showToast }) {
  const [resourceType, setResourceType] = useState('')
  const [action, setAction] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [viewing, setViewing] = useState(null)

  const params = new URLSearchParams()
  if (resourceType) params.set('resource_type', resourceType)
  if (action) params.set('action', action)
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  params.set('per_page', '100')
  const path = `/api/audit-logs?${params.toString()}`
  const auditApi = useApiResource(path, { listKey: 'audit_logs', itemKey: 'audit_log' })

  const columns = [
    { key: 'created_at', label: 'When', sortable: true, render: r => new Date(r.created_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }) },
    { key: 'actor', label: 'Actor', sortable: true },
    { key: 'action', label: 'Action', render: r => <span className="rounded-full bg-kTint px-2.5 py-1 text-xs font-bold text-kOrange">{r.action}</span> },
    { key: 'resource_type', label: 'Resource', sortable: true, render: r => <span>{r.resource_type} <span className="text-kMuted">#{r.resource_id}</span></span> },
  ]

  return <Shell>
    <div><div className="eyebrow">Administration</div><h1 className="font-display text-3xl font-bold text-kGreen">Audit Logs</h1></div>
    <p className="mt-2 max-w-2xl text-sm text-kMuted">Every sensitive action taken on the platform — user and role changes, verifications, financial records, session revocations, and 2FA changes — newest first.</p>

    <div className="mt-6 flex flex-wrap items-center gap-3">
      <select value={resourceType} onChange={e => setResourceType(e.target.value)} className="input-k w-48">
        <option value="">All resource types</option>{RESOURCE_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
      </select>
      <select value={action} onChange={e => setAction(e.target.value)} className="input-k w-44">
        <option value="">All actions</option>{ACTIONS.map(a => <option key={a} value={a}>{a}</option>)}
      </select>
      <label className="text-xs font-semibold text-kMuted">From<input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} className="input-k mt-1" /></label>
      <label className="text-xs font-semibold text-kMuted">To<input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} className="input-k mt-1" /></label>
    </div>

    <div className="mt-4">
      <DataTable
        columns={columns}
        data={auditApi.items}
        loading={auditApi.loading}
        error={auditApi.error}
        onRetry={auditApi.reload}
        emptyMessage="No audit events match these filters."
        onRowClick={setViewing}
        minWidth={800}
        pageSize={20}
      />
    </div>
    {!auditApi.loading && !auditApi.error && auditApi.items.length === 0 && (
      <div className="mt-4 flex items-center gap-2 text-xs text-kMuted"><History size={14} /> Nothing recorded yet for these filters.</div>
    )}

    {viewing && <AuditDetailModal entry={viewing} onClose={() => setViewing(null)} />}
  </Shell>
}
