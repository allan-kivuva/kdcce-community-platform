import { useState } from 'react'
import { Search, Plus, Pencil, Trash2 } from 'lucide-react'
import Shell from '../../components/admin/Shell'
import Modal from '../../components/admin/Modal'
import { LoadingState, ErrorState, errorMessage } from '../../components/admin/adminHelpers'
import { useApiResource } from '../../lib/useApiResource'
import { getStoredUser } from '../../lib/api'

const GENDERS = ['Male', 'Female', 'Other']
const STATUSES = ['Active', 'Inactive', 'Deceased', 'Transferred']

function OpaPanel({ opas, loading, createOpa, showToast }) {
  const [name, setName] = useState('')
  const [location, setLocation] = useState('')
  const [saving, setSaving] = useState(false)

  async function add(e) {
    e.preventDefault()
    setSaving(true)
    try {
      await createOpa({ name, location: location || null })
      setName(''); setLocation('')
      showToast('OPA added')
    } catch (err) { showToast(errorMessage(err)) }
    finally { setSaving(false) }
  }

  return <div className="card-k p-6">
    <h2 className="font-display text-lg font-bold text-kGreen">OPA / community groups</h2>
    {loading ? <p className="mt-3 text-sm text-kMuted">Loading…</p> : <ul className="mt-4 grid gap-2 text-sm">
      {opas.map(o => <li key={o.id} className="rounded-xl border border-kBorder px-4 py-2"><span className="font-semibold text-kInk">{o.name}</span>{o.location && <span className="text-kMuted"> &middot; {o.location}</span>}</li>)}
      {opas.length === 0 && <li className="text-kMuted">No OPAs yet.</li>}
    </ul>}
    <form onSubmit={add} className="mt-4 grid gap-3">
      <input value={name} onChange={e => setName(e.target.value)} className="input-k" placeholder="OPA name" required />
      <input value={location} onChange={e => setLocation(e.target.value)} className="input-k" placeholder="Location (optional)" />
      <button disabled={saving} className="btn-orange w-fit disabled:opacity-60"><Plus size={16} /> {saving ? 'Adding…' : 'Add OPA'}</button>
    </form>
  </div>
}

export default function ElderlyManager({ showToast }) {
  const membersApi = useApiResource('/api/elderly', { listKey: 'members', itemKey: 'member' })
  const opasApi = useApiResource('/api/opas', { listKey: 'opas', itemKey: 'opa' })
  const [q, setQ] = useState('')
  const [statusFilter, setStatusFilter] = useState('All')
  const [modal, setModal] = useState(null)
  const [saving, setSaving] = useState(false)
  const isAdmin = getStoredUser()?.role === 'admin'

  const filtered = membersApi.items.filter(m =>
    (statusFilter === 'All' || m.status === statusFilter) &&
    (m.full_name.toLowerCase().includes(q.toLowerCase()) || m.member_id.toLowerCase().includes(q.toLowerCase()))
  )

  async function save(e) {
    e.preventDefault()
    const f = new FormData(e.target)
    const opaVal = f.get('opa_id')
    const data = {
      full_name: f.get('full_name'),
      gender: f.get('gender'),
      date_of_birth: f.get('date_of_birth') || null,
      location: f.get('location') || null,
      opa_id: opaVal ? Number(opaVal) : null,
      status: f.get('status'),
      emergency_contact_name: f.get('emergency_contact_name') || null,
      emergency_contact_phone: f.get('emergency_contact_phone') || null,
      emergency_contact_relationship: f.get('emergency_contact_relationship') || null,
      vulnerability_notes: f.get('vulnerability_notes') || null,
      health_notes: f.get('health_notes') || null,
      allergies: f.get('allergies') || null,
      dietary_requirements: f.get('dietary_requirements') || null,
    }
    setSaving(true)
    try {
      if (modal.data) { await membersApi.patch(modal.data.id, data); showToast('Member updated') }
      else { await membersApi.create(data); showToast('Member registered') }
      setModal(null)
    } catch (err) { showToast(errorMessage(err)) }
    finally { setSaving(false) }
  }

  async function remove(m) {
    if (!window.confirm(`Remove ${m.full_name}'s record? This cannot be undone.`)) return
    try { await membersApi.remove(m.id); showToast('Member removed') }
    catch (err) { showToast(errorMessage(err)) }
  }

  return <Shell>
    <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
      <div><div className="eyebrow">Manage</div><h1 className="font-display text-3xl font-bold text-kGreen">Elderly members</h1></div>
      <button onClick={() => setModal({})} className="btn-green"><Plus size={16} /> Register member</button>
    </div>

    <div className="mt-7 grid gap-6 xl:grid-cols-[1fr_320px]">
      <div>
        {membersApi.loading ? <LoadingState label="members" /> : membersApi.error ? <ErrorState message={membersApi.error} onRetry={membersApi.reload} /> : <div className="card-k overflow-hidden">
          <div className="flex flex-col gap-3 border-b border-kBorderSoft p-5 sm:flex-row">
            <div className="relative flex-1"><Search className="absolute left-3 top-3.5 text-kMuted" size={17} /><input value={q} onChange={e => setQ(e.target.value)} className="input-k pl-10" placeholder="Search name or member ID..." /></div>
            <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="rounded-xl border border-kBorder bg-kSurface px-4 py-3 text-sm text-kInk"><option>All</option>{STATUSES.map(s => <option key={s}>{s}</option>)}</select>
          </div>
          <div className="overflow-x-auto"><table className="w-full min-w-[700px] text-left text-sm"><thead className="bg-kBorderSoft text-xs uppercase tracking-wider text-kMuted"><tr><th className="px-5 py-4">Member ID</th><th className="px-5 py-4">Name</th><th className="px-5 py-4">Gender</th><th className="px-5 py-4">OPA</th><th className="px-5 py-4">Status</th><th className="px-5 py-4">Actions</th></tr></thead><tbody>
            {filtered.map(m => <tr key={m.id} className="border-b border-kBorderSoft"><td className="px-5 py-4 text-kMuted">{m.member_id}</td><td className="px-5 py-4 font-semibold text-kInk">{m.full_name}</td><td className="px-5 py-4 text-kMuted">{m.gender}</td><td className="px-5 py-4 text-kMuted">{m.opa_name || '—'}</td><td className="px-5 py-4 text-kMuted">{m.status}</td><td className="px-5 py-4"><div className="flex gap-3"><button onClick={() => setModal({ data: m })} className="text-kOrange"><Pencil size={16} /></button>{isAdmin && <button onClick={() => remove(m)} className="text-kMuted hover:text-red-600"><Trash2 size={16} /></button>}</div></td></tr>)}
            {filtered.length === 0 && <tr><td colSpan={6} className="px-5 py-10 text-center text-sm text-kMuted">No members match your search.</td></tr>}
          </tbody></table></div>
        </div>}
      </div>
      <OpaPanel opas={opasApi.items} loading={opasApi.loading} createOpa={opasApi.create} showToast={showToast} />
    </div>

    {modal && <Modal title={modal.data ? 'Edit member' : 'Register elderly member'} onClose={() => setModal(null)}>
      <form onSubmit={save} className="grid gap-4">
        <label className="text-sm font-semibold">Full name<input name="full_name" defaultValue={modal.data?.full_name} className="input-k mt-2" required /></label>
        <div className="grid grid-cols-2 gap-4">
          <label className="text-sm font-semibold">Gender<select name="gender" defaultValue={modal.data?.gender || 'Female'} className="input-k mt-2">{GENDERS.map(g => <option key={g}>{g}</option>)}</select></label>
          <label className="text-sm font-semibold">Date of birth<input name="date_of_birth" type="date" defaultValue={modal.data?.date_of_birth || ''} className="input-k mt-2" /></label>
        </div>
        <label className="text-sm font-semibold">Location<input name="location" defaultValue={modal.data?.location} className="input-k mt-2" /></label>
        <div className="grid grid-cols-2 gap-4">
          <label className="text-sm font-semibold">OPA / community group<select name="opa_id" defaultValue={modal.data?.opa_id || ''} className="input-k mt-2"><option value="">None</option>{opasApi.items.map(o => <option key={o.id} value={o.id}>{o.name}</option>)}</select></label>
          <label className="text-sm font-semibold">Status<select name="status" defaultValue={modal.data?.status || 'Active'} className="input-k mt-2">{STATUSES.map(s => <option key={s}>{s}</option>)}</select></label>
        </div>

        <div className="mt-1 text-xs font-bold uppercase tracking-wider text-kMuted">Emergency contact</div>
        <div className="grid grid-cols-2 gap-4">
          <label className="text-sm font-semibold">Name<input name="emergency_contact_name" defaultValue={modal.data?.emergency_contact_name} className="input-k mt-2" /></label>
          <label className="text-sm font-semibold">Phone<input name="emergency_contact_phone" defaultValue={modal.data?.emergency_contact_phone} className="input-k mt-2" /></label>
        </div>
        <label className="text-sm font-semibold">Relationship<input name="emergency_contact_relationship" defaultValue={modal.data?.emergency_contact_relationship} className="input-k mt-2" /></label>

        <div className="mt-1 text-xs font-bold uppercase tracking-wider text-kMuted">Health &amp; vulnerability — visible to staff/admin only</div>
        <label className="text-sm font-semibold">Vulnerability notes<textarea name="vulnerability_notes" defaultValue={modal.data?.vulnerability_notes} rows={2} className="input-k mt-2" /></label>
        <label className="text-sm font-semibold">Health notes<textarea name="health_notes" defaultValue={modal.data?.health_notes} rows={2} className="input-k mt-2" /></label>
        <label className="text-sm font-semibold">Allergies<textarea name="allergies" defaultValue={modal.data?.allergies} rows={2} className="input-k mt-2" /></label>
        <label className="text-sm font-semibold">Dietary requirements<textarea name="dietary_requirements" defaultValue={modal.data?.dietary_requirements} rows={2} className="input-k mt-2" /></label>

        <button disabled={saving} className="btn-orange mt-2 disabled:opacity-60">{saving ? 'Saving…' : modal.data ? 'Save changes' : 'Register member'}</button>
      </form>
    </Modal>}
  </Shell>
}
