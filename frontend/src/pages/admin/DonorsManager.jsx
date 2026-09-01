import { useState, useEffect } from 'react'
import { Search, Plus } from 'lucide-react'
import Shell from '../../components/admin/Shell'
import Modal from '../../components/admin/Modal'
import DataTable from '../../components/admin/DataTable'
import StatusBadge from '../../components/admin/StatusBadge'
import { errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch } from '../../lib/api'
import { useApiResource } from '../../lib/useApiResource'

const DONOR_TYPES = ['Individual', 'Organization', 'Anonymous']

function fmtMoney(n) { return `KES ${Number(n || 0).toLocaleString()}` }
function fmtDate(iso) { return iso ? new Date(iso).toLocaleDateString([], { dateStyle: 'medium' }) : '—' }

function DonorFormModal({ onClose, onSaved, showToast }) {
  const [saving, setSaving] = useState(false)
  async function save(e) {
    e.preventDefault()
    const f = new FormData(e.target)
    setSaving(true)
    try {
      await apiFetch('/api/donors', {
        method: 'POST',
        body: {
          name: f.get('name'), email: f.get('email') || null, phone: f.get('phone') || null,
          organization: f.get('organization') || null, donor_type: f.get('donor_type'), notes: f.get('notes') || null,
        },
      })
      showToast('Donor created')
      onSaved()
      onClose()
    } catch (err) { showToast(errorMessage(err)) }
    finally { setSaving(false) }
  }
  return <Modal title="New donor" onClose={onClose}>
    <form onSubmit={save} className="grid gap-4">
      <label className="text-sm font-semibold">Name<input name="name" className="input-k mt-2" required /></label>
      <div className="grid grid-cols-2 gap-4">
        <label className="text-sm font-semibold">Email<input name="email" type="email" className="input-k mt-2" /></label>
        <label className="text-sm font-semibold">Phone<input name="phone" className="input-k mt-2" /></label>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <label className="text-sm font-semibold">Type<select name="donor_type" defaultValue="Individual" className="input-k mt-2">{DONOR_TYPES.map(t => <option key={t}>{t}</option>)}</select></label>
        <label className="text-sm font-semibold">Organization<input name="organization" className="input-k mt-2" /></label>
      </div>
      <label className="text-sm font-semibold">Notes (internal only)<textarea name="notes" rows={2} className="input-k mt-2" /></label>
      <button disabled={saving} className="btn-orange mt-2 disabled:opacity-60">{saving ? 'Creating…' : 'Create donor'}</button>
    </form>
  </Modal>
}

function DonorDetailModal({ donor, onClose, onSaved, showToast }) {
  const [tab, setTab] = useState('overview')
  const [detail, setDetail] = useState(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => { apiFetch(`/api/donors/${donor.id}`).then(setDetail).catch(err => showToast(errorMessage(err))) }, [donor.id, showToast])

  async function saveNotes(e) {
    e.preventDefault()
    const notes = new FormData(e.target).get('notes')
    setSaving(true)
    try { await apiFetch(`/api/donors/${donor.id}`, { method: 'PATCH', body: { notes } }); showToast('Notes saved'); onSaved() }
    catch (err) { showToast(errorMessage(err)) }
    finally { setSaving(false) }
  }

  if (!detail) return <Modal title="Donor details" onClose={onClose}><p className="text-sm text-kMuted">Loading…</p></Modal>
  const { donor: d, donations } = detail

  return <Modal title="Donor details" onClose={onClose} wide>
    <div className="-mt-2 mb-4">
      <div className="flex items-center gap-2"><span className="font-display text-lg font-bold text-kGreen">{d.name}</span><StatusBadge value={d.donor_type} /></div>
      <div className="text-xs text-kMuted">{d.email || 'No email'}{d.phone ? ` · ${d.phone}` : ''}{d.organization ? ` · ${d.organization}` : ''}</div>
    </div>
    <div className="flex gap-1 border-b border-kBorderSoft pb-2">
      {['overview', 'donations', 'campaigns'].map(t => <button key={t} onClick={() => setTab(t)} className={`shrink-0 rounded-lg px-3 py-1.5 text-sm font-semibold capitalize ${tab === t ? 'bg-kOrange text-white' : 'text-kMuted hover:bg-kCream'}`}>{t}</button>)}
    </div>
    <div className="mt-4">
      {tab === 'overview' && <div className="grid gap-4">
        <div className="grid grid-cols-3 gap-3 text-center">
          <div className="card-k p-3"><div className="font-display text-xl font-bold text-kGreen">{fmtMoney(d.lifetime_amount)}</div><div className="text-xs text-kMuted">Lifetime</div></div>
          <div className="card-k p-3"><div className="font-display text-xl font-bold text-kGreen">{d.donation_count}</div><div className="text-xs text-kMuted">Donations</div></div>
          <div className="card-k p-3"><div className="font-display text-sm font-bold text-kInk">{fmtDate(d.most_recent_donation_at)}</div><div className="text-xs text-kMuted">Most recent</div></div>
        </div>
        <form onSubmit={saveNotes} className="grid gap-2">
          <label className="text-xs font-bold uppercase tracking-wide text-kMuted">Internal notes (never shown publicly)<textarea name="notes" defaultValue={d.notes} rows={3} className="input-k mt-2" /></label>
          <button disabled={saving} className="btn-orange w-fit disabled:opacity-60">{saving ? 'Saving…' : 'Save notes'}</button>
        </form>
      </div>}
      {tab === 'donations' && <div className="grid gap-2">
        {donations.map(don => <div key={don.id} className="flex items-center justify-between rounded-xl bg-kCream px-3 py-2.5">
          <div><div className="text-sm font-semibold text-kInk">{don.donation_type === 'Cash' ? fmtMoney(don.amount) : `${don.quantity ?? ''} ${don.unit || ''}`.trim()}</div><div className="text-xs text-kMuted">{fmtDate(don.created_at)}{don.campaign ? ` · ${don.campaign}` : ''}</div></div>
          <StatusBadge value={don.status} />
        </div>)}
        {donations.length === 0 && <p className="text-sm text-kMuted">No donations recorded.</p>}
      </div>}
      {tab === 'campaigns' && <div className="grid gap-1.5">
        {(d.campaigns_supported || []).map(c => <div key={c} className="rounded-xl bg-kCream px-3 py-2 text-sm text-kInk">{c}</div>)}
        {(d.campaigns_supported || []).length === 0 && <p className="text-sm text-kMuted">No campaigns supported yet.</p>}
      </div>}
    </div>
  </Modal>
}

export default function DonorsManager({ showToast }) {
  const donorsApi = useApiResource('/api/donors', { listKey: 'donors', itemKey: 'donor' })
  const [q, setQ] = useState('')
  const [creating, setCreating] = useState(false)
  const [viewing, setViewing] = useState(null)

  const filtered = donorsApi.items.filter(d =>
    d.name.toLowerCase().includes(q.toLowerCase()) || (d.email || '').toLowerCase().includes(q.toLowerCase())
  )

  const columns = [
    { key: 'name', label: 'Name', sortable: true, render: d => <span className="font-semibold text-kInk">{d.name}</span> },
    { key: 'email', label: 'Contact', render: d => <span className="text-kMuted">{d.email || '—'}{d.phone ? ` · ${d.phone}` : ''}</span> },
    { key: 'donor_type', label: 'Type', sortable: true, render: d => <StatusBadge value={d.donor_type} /> },
    { key: 'organization', label: 'Organization', render: d => <span className="text-kMuted">{d.organization || '—'}</span> },
    { key: 'action', label: 'Action', render: d => <button onClick={() => setViewing(d)} className="text-xs font-bold text-kOrange">View</button> },
  ]

  return <Shell>
    <div className="flex items-center justify-between">
      <div><div className="eyebrow">Finance</div><h1 className="font-display text-3xl font-bold text-kGreen">Donors</h1></div>
      <button onClick={() => setCreating(true)} className="btn-orange"><Plus size={16} /> New donor</button>
    </div>

    <div className="mt-7">
      <DataTable
        columns={columns} data={filtered} loading={donorsApi.loading} error={donorsApi.error} onRetry={donorsApi.reload}
        emptyMessage="No donors match your search." minWidth={700}
        header={<div className="relative flex-1"><Search className="absolute left-3 top-3.5 text-kMuted" size={17} /><input value={q} onChange={e => setQ(e.target.value)} className="input-k pl-10" placeholder="Search name or email..." /></div>}
      />
    </div>

    {creating && <DonorFormModal onClose={() => setCreating(false)} onSaved={donorsApi.reload} showToast={showToast} />}
    {viewing && <DonorDetailModal donor={viewing} onClose={() => setViewing(null)} onSaved={donorsApi.reload} showToast={showToast} />}
  </Shell>
}
