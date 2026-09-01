import { useState } from 'react'
import { BadgeCheck, Search, ShieldCheck } from 'lucide-react'
import Shell from '../../components/admin/Shell'
import Modal from '../../components/admin/Modal'
import StatusBadge from '../../components/admin/StatusBadge'
import DataTable from '../../components/admin/DataTable'
import VolunteerDetailModal from '../../components/admin/VolunteerDetailModal'
import { errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch } from '../../lib/api'
import { useApiResource } from '../../lib/useApiResource'

function VerifyIdModal({ onClose, showToast }) {
  const [checking, setChecking] = useState(false)
  const [result, setResult] = useState(null)

  async function check(e) {
    e.preventDefault()
    const token = new FormData(e.target).get('token')?.trim()
    if (!token) return
    setChecking(true)
    setResult(null)
    try {
      const data = await apiFetch('/api/volunteers/qr/verify', { method: 'POST', body: { token } })
      setResult({ ok: true, digitalId: data.digital_id })
    } catch (err) { setResult({ ok: false, message: errorMessage(err) }) }
    finally { setChecking(false) }
  }

  return <Modal title="Verify volunteer ID" onClose={onClose}>
    <form onSubmit={check} className="grid gap-3">
      <label className="text-sm font-semibold">
        Code from volunteer's Digital ID
        <textarea name="token" rows={3} className="input-k mt-2 font-mono text-xs" placeholder="Paste or enter the code shown on the volunteer's app" required />
      </label>
      <p className="text-xs text-kMuted">The volunteer shows this code from their Digital ID page (My Volunteer Portal → Digital ID). It expires 5 minutes after generation. Scanning it directly with a camera isn't supported yet — enter it manually here.</p>
      <button disabled={checking} className="btn-orange justify-center disabled:opacity-60">{checking ? 'Checking…' : 'Verify'}</button>
    </form>
    {result && (result.ok ? <div className="mt-4 flex items-center gap-3 rounded-xl bg-emerald-500/10 p-4">
      <ShieldCheck size={20} className="shrink-0 text-emerald-500" />
      <div><div className="font-semibold text-kInk">{result.digitalId.name}</div><div className="text-xs text-kMuted">{result.digitalId.volunteer_code} &middot; {result.digitalId.status}</div></div>
    </div> : <div className="mt-4 rounded-xl bg-red-500/10 p-4 text-sm font-semibold text-red-500">{result.message}</div>)}
  </Modal>
}

export default function VolunteerManager({ showToast }) {
  const volunteersApi = useApiResource('/api/volunteers', { listKey: 'volunteers', itemKey: 'volunteer' })
  const [q, setQ] = useState('')
  const [statusFilter, setStatusFilter] = useState('All')
  const [reviewing, setReviewing] = useState(null)
  const [verifying, setVerifying] = useState(false)

  const filtered = volunteersApi.items.filter(v =>
    (statusFilter === 'All' || v.status === statusFilter) &&
    (v.name.toLowerCase().includes(q.toLowerCase()) || v.email.toLowerCase().includes(q.toLowerCase()))
  )

  const columns = [
    { key: 'name', label: 'Name', sortable: true, render: v => <span className="font-semibold text-kInk">{v.name}</span> },
    { key: 'email', label: 'Contact', sortable: true, render: v => <span className="text-kMuted">{v.email}{v.phone ? ` · ${v.phone}` : ''}</span> },
    { key: 'skills', label: 'Skills', render: v => <span className="text-kMuted">{v.skills || '—'}</span> },
    { key: 'availability', label: 'Availability', render: v => <span className="text-kMuted">{v.availability || '—'}</span> },
    { key: 'status', label: 'Status', sortable: true, render: v => <StatusBadge value={v.status} /> },
    { key: 'action', label: 'Action', render: v => <button onClick={() => setReviewing(v)} className="text-xs font-bold text-kOrange">{v.status === 'Pending' ? 'Review' : 'View'}</button> },
  ]

  return <Shell>
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div><div className="eyebrow">Manage</div><h1 className="font-display text-3xl font-bold text-kGreen">Volunteer Applications</h1></div>
      <button onClick={() => setVerifying(true)} className="flex items-center gap-2 rounded-xl border border-kBorder px-4 py-2.5 text-sm font-bold text-kMuted hover:bg-kCream"><BadgeCheck size={16} /> Verify ID</button>
    </div>

    <div className="mt-7">
      <DataTable
        columns={columns}
        data={filtered}
        loading={volunteersApi.loading}
        error={volunteersApi.error}
        onRetry={volunteersApi.reload}
        emptyMessage="No volunteers match your search."
        minWidth={800}
        header={<>
          <div className="relative flex-1"><Search className="absolute left-3 top-3.5 text-kMuted" size={17} /><input value={q} onChange={e => setQ(e.target.value)} className="input-k pl-10" placeholder="Search name or email..." /></div>
          <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="rounded-xl border border-kBorder bg-kSurface px-4 py-3 text-sm text-kInk"><option>All</option><option>Pending</option><option>Verified</option><option>Rejected</option></select>
        </>}
      />
    </div>

    {reviewing && <VolunteerDetailModal volunteer={reviewing} onClose={() => setReviewing(null)} onDecide={(id, data) => volunteersApi.patch(id, data)} showToast={showToast} />}
    {verifying && <VerifyIdModal onClose={() => setVerifying(false)} showToast={showToast} />}
  </Shell>
}
