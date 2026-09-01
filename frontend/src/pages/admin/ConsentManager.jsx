import { useEffect, useState } from 'react'
import { History, Plus } from 'lucide-react'
import Shell from '../../components/admin/Shell'
import Modal from '../../components/admin/Modal'
import StatusBadge from '../../components/admin/StatusBadge'
import DataTable from '../../components/admin/DataTable'
import { errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch } from '../../lib/api'
import { useApiResource } from '../../lib/useApiResource'

const CONSENT_TYPES = ['Family Portal Access', 'Photo Use', 'Communication', 'Program Participation', 'Data Sharing', 'Emergency Contact Access']
const CONSENT_STATUSES = ['Granted', 'Denied', 'Withdrawn', 'Pending']

function RecordConsentModal({ members, onClose, onSaved, showToast }) {
  const [saving, setSaving] = useState(false)

  async function save(e) {
    e.preventDefault()
    const f = new FormData(e.target)
    setSaving(true)
    try {
      await apiFetch('/api/consents', {
        method: 'POST',
        body: {
          elderly_member_id: Number(f.get('elderly_member_id')),
          consent_type: f.get('consent_type'),
          status: f.get('status'),
          notes: f.get('notes') || null,
        },
      })
      showToast('Consent decision recorded')
      onSaved()
      onClose()
    } catch (err) { showToast(errorMessage(err)) }
    finally { setSaving(false) }
  }

  return <Modal title="Record consent decision" onClose={onClose}>
    <form onSubmit={save} className="grid gap-4">
      <label className="text-sm font-semibold">Elderly member
        <select name="elderly_member_id" className="input-k mt-2" required>
          <option value="">Select a member…</option>
          {members.map(m => <option key={m.id} value={m.id}>{m.full_name} ({m.member_id})</option>)}
        </select>
      </label>
      <label className="text-sm font-semibold">Consent type
        <select name="consent_type" className="input-k mt-2" required>{CONSENT_TYPES.map(t => <option key={t}>{t}</option>)}</select>
      </label>
      <label className="text-sm font-semibold">Status
        <select name="status" className="input-k mt-2" required>{CONSENT_STATUSES.map(s => <option key={s}>{s}</option>)}</select>
      </label>
      <label className="text-sm font-semibold">Notes (optional)<textarea name="notes" rows={3} className="input-k mt-2" /></label>
      <button disabled={saving} className="btn-orange mt-2 disabled:opacity-60">{saving ? 'Saving…' : 'Record decision'}</button>
    </form>
  </Modal>
}

function HistoryModal({ memberId, memberName, consentType, onClose }) {
  const [rows, setRows] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    apiFetch(`/api/consents?history=true&elderly_member_id=${memberId}&consent_type=${encodeURIComponent(consentType)}`)
      .then(d => { if (!cancelled) setRows(d.consents) })
      .catch(err => { if (!cancelled) setError(errorMessage(err)) })
    return () => { cancelled = true }
  }, [memberId, consentType])

  return <Modal title={`${consentType} history — ${memberName}`} onClose={onClose} wide>
    {error && <p className="text-sm text-red-500">{error}</p>}
    {!error && rows === null && <p className="text-sm text-kMuted">Loading…</p>}
    {!error && rows && rows.length === 0 && <p className="text-sm text-kMuted">No history recorded.</p>}
    {!error && rows && rows.length > 0 && <div className="grid gap-2">
      {rows.map(c => <div key={c.id} className="rounded-xl bg-kCream px-4 py-3">
        <div className="flex items-center justify-between">
          <StatusBadge value={c.status} />
          <span className="text-xs text-kMuted">{new Date(c.created_at).toLocaleString()}</span>
        </div>
        <div className="mt-1 text-xs text-kMuted">Recorded by {c.recorded_by || 'Unknown'}{c.granted_at && ` · Granted ${new Date(c.granted_at).toLocaleDateString()}`}{c.withdrawn_at && ` · Withdrawn ${new Date(c.withdrawn_at).toLocaleDateString()}`}</div>
        {c.notes && <p className="mt-1 text-sm text-kInk">{c.notes}</p>}
      </div>)}
    </div>}
  </Modal>
}

export default function ConsentManager({ showToast }) {
  const [members, setMembers] = useState([])
  const [memberFilter, setMemberFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [formOpen, setFormOpen] = useState(false)
  const [historyFor, setHistoryFor] = useState(null)

  useEffect(() => { apiFetch('/api/elderly').then(d => setMembers(d.members)).catch(() => {}) }, [])

  const params = new URLSearchParams()
  if (memberFilter) params.set('elderly_member_id', memberFilter)
  if (typeFilter) params.set('consent_type', typeFilter)
  const path = `/api/consents?${params.toString()}`
  const consentsApi = useApiResource(path, { listKey: 'consents', itemKey: 'consent' })

  const columns = [
    { key: 'elderly_member_name', label: 'Member', sortable: true },
    { key: 'consent_type', label: 'Consent type', sortable: true },
    { key: 'status', label: 'Status', sortable: true, render: c => <StatusBadge value={c.status} /> },
    { key: 'granted_at', label: 'Granted', render: c => c.granted_at ? new Date(c.granted_at).toLocaleDateString() : '—' },
    { key: 'withdrawn_at', label: 'Withdrawn', render: c => c.withdrawn_at ? new Date(c.withdrawn_at).toLocaleDateString() : '—' },
    { key: 'recorded_by', label: 'Recorded by' },
    { key: 'actions', label: '', align: 'right', render: c => <button onClick={() => setHistoryFor(c)} className="flex items-center gap-1 text-xs font-bold text-kOrange"><History size={13} /> History</button> },
  ]

  return <Shell>
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div><div className="eyebrow">Compliance</div><h1 className="font-display text-3xl font-bold text-kGreen">Consents</h1></div>
      <button onClick={() => setFormOpen(true)} className="btn-orange"><Plus size={16} /> Record consent decision</button>
    </div>
    <p className="mt-2 max-w-2xl text-sm text-kMuted">Every grant, denial, or withdrawal is recorded as a new entry — the log below shows each member's current status per consent type.</p>

    <div className="mt-6 flex flex-wrap items-center gap-3">
      <select value={memberFilter} onChange={e => setMemberFilter(e.target.value)} className="input-k w-56">
        <option value="">All members</option>
        {members.map(m => <option key={m.id} value={m.id}>{m.full_name}</option>)}
      </select>
      <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)} className="input-k w-56">
        <option value="">All consent types</option>
        {CONSENT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
      </select>
    </div>

    <div className="mt-4">
      <DataTable
        columns={columns}
        data={consentsApi.items}
        loading={consentsApi.loading}
        error={consentsApi.error}
        onRetry={consentsApi.reload}
        emptyMessage="No consent decisions recorded yet."
        minWidth={800}
      />
    </div>

    {formOpen && <RecordConsentModal members={members} onClose={() => setFormOpen(false)} onSaved={consentsApi.reload} showToast={showToast} />}
    {historyFor && <HistoryModal memberId={historyFor.elderly_member_id} memberName={historyFor.elderly_member_name} consentType={historyFor.consent_type} onClose={() => setHistoryFor(null)} />}
  </Shell>
}
