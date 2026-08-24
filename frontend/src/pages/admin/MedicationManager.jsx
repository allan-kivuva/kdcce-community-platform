import { useState, useEffect, useCallback } from 'react'
import { Search, Plus, Check, X as XIcon, MinusCircle, ChevronDown, ChevronUp } from 'lucide-react'
import Shell from '../../components/admin/Shell'
import Modal from '../../components/admin/Modal'
import { LoadingState, ErrorState, errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch } from '../../lib/api'

const STATUSES = ['Active', 'Completed', 'Discontinued']

function fmt(iso) { return new Date(iso).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }) }

function AdministrationLog({ medication, showToast }) {
  const [open, setOpen] = useState(false)
  const [entries, setEntries] = useState([])
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try { setEntries((await apiFetch(`/api/medications/${medication.id}/administrations`)).administrations) }
    catch (err) { showToast(errorMessage(err)) }
    finally { setLoading(false) }
  }, [medication.id, showToast])

  useEffect(() => { if (open) load() }, [open, load])

  async function log(status) {
    setBusy(true)
    try {
      await apiFetch(`/api/medications/${medication.id}/administrations`, { method: 'POST', body: { status } })
      showToast(`Dose logged: ${status}`)
      load()
    } catch (err) { showToast(errorMessage(err)) }
    finally { setBusy(false) }
  }

  return <div className="border-t border-kBorderSoft bg-kCream/50 px-5 py-4">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <button onClick={() => setOpen(o => !o)} className="flex items-center gap-1 text-sm font-semibold text-kGreen">{open ? <ChevronUp size={16} /> : <ChevronDown size={16} />} Administration log</button>
      {medication.status === 'Active' && <div className="flex gap-2">
        <button disabled={busy} onClick={() => log('Given')} className="flex items-center gap-1 rounded-lg bg-kGreen px-3 py-1.5 text-xs font-bold text-white disabled:opacity-60"><Check size={14} /> Given</button>
        <button disabled={busy} onClick={() => log('Missed')} className="flex items-center gap-1 rounded-lg border border-kBorder px-3 py-1.5 text-xs font-bold text-kMuted disabled:opacity-60"><MinusCircle size={14} /> Missed</button>
        <button disabled={busy} onClick={() => log('Refused')} className="flex items-center gap-1 rounded-lg border border-kBorder px-3 py-1.5 text-xs font-bold text-kMuted disabled:opacity-60"><XIcon size={14} /> Refused</button>
      </div>}
    </div>
    {open && (loading ? <p className="mt-3 text-sm text-kMuted">Loading…</p> : <ul className="mt-3 grid gap-1 text-sm">
      {entries.map(e => <li key={e.id} className="flex justify-between text-kMuted"><span className="font-semibold text-kInk">{e.status}</span><span>{fmt(e.administered_at)} &middot; {e.administered_by}</span></li>)}
      {entries.length === 0 && <li className="text-kMuted">No doses logged yet.</li>}
    </ul>)}
  </div>
}

export default function MedicationManager({ showToast }) {
  const [members, setMembers] = useState([])
  const [membersLoading, setMembersLoading] = useState(true)
  const [q, setQ] = useState('')
  const [selected, setSelected] = useState(null)
  const [medications, setMedications] = useState([])
  const [medsLoading, setMedsLoading] = useState(false)
  const [error, setError] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [saving, setSaving] = useState(false)

  const loadMembers = useCallback(async () => {
    setMembersLoading(true)
    try { setMembers((await apiFetch('/api/elderly')).members) }
    catch (err) { setError(errorMessage(err)) }
    finally { setMembersLoading(false) }
  }, [])

  useEffect(() => { loadMembers() }, [loadMembers])

  const loadMedications = useCallback(async (memberId) => {
    setMedsLoading(true)
    setError('')
    try { setMedications((await apiFetch(`/api/medications?elderly_member_id=${memberId}`)).medications) }
    catch (err) { setError(errorMessage(err)) }
    finally { setMedsLoading(false) }
  }, [])

  function selectMember(m) {
    setSelected(m)
    setQ('')
    loadMedications(m.id)
  }

  const query = q.trim().toLowerCase()
  const results = query
    ? members.filter(m => m.full_name.toLowerCase().includes(query) || m.member_id.toLowerCase().includes(query)).slice(0, 8)
    : []

  async function save(e) {
    e.preventDefault()
    const f = new FormData(e.target)
    const data = {
      elderly_member_id: selected.id,
      name: f.get('name'),
      dosage: f.get('dosage') || null,
      instructions: f.get('instructions') || null,
      schedule: f.get('schedule') || null,
      start_date: f.get('start_date') || undefined,
      end_date: f.get('end_date') || null,
      notes: f.get('notes') || null,
    }
    setSaving(true)
    try {
      await apiFetch('/api/medications', { method: 'POST', body: data })
      showToast('Medication added')
      setModalOpen(false)
      loadMedications(selected.id)
    } catch (err) { showToast(errorMessage(err)) }
    finally { setSaving(false) }
  }

  async function setStatus(medication, status) {
    try {
      await apiFetch(`/api/medications/${medication.id}`, { method: 'PATCH', body: { status } })
      showToast(`Marked ${status}`)
      loadMedications(selected.id)
    } catch (err) { showToast(errorMessage(err)) }
  }

  return <Shell>
    <div><div className="eyebrow">Manage</div><h1 className="font-display text-3xl font-bold text-kGreen">Medication</h1></div>

    <div className="card-k mt-7 p-6">
      <h2 className="font-display text-lg font-bold text-kGreen">Find a member</h2>
      <div className="relative mt-4"><Search className="absolute left-3 top-3.5 text-kMuted" size={17} /><input value={q} onChange={e => setQ(e.target.value)} className="input-k pl-10" placeholder="Search by name or member ID..." /></div>
      {membersLoading ? <p className="mt-3 text-sm text-kMuted">Loading members…</p> : query && <div className="mt-3 grid gap-2">
        {results.length === 0 && <p className="text-sm text-kMuted">No matching member.</p>}
        {results.map(m => <button key={m.id} onClick={() => selectMember(m)} className="flex items-center justify-between rounded-xl border border-kBorder px-4 py-3 text-left hover:bg-kCream">
          <div><div className="text-sm font-semibold text-kInk">{m.full_name}</div><div className="text-xs text-kMuted">{m.member_id} &middot; {m.gender}</div></div>
        </button>)}
      </div>}
    </div>

    {selected && <div className="card-k mt-6 overflow-hidden">
      <div className="flex items-center justify-between border-b border-kBorderSoft p-5">
        <div><h2 className="font-display text-lg font-bold text-kGreen">{selected.full_name}</h2><p className="text-xs text-kMuted">{selected.member_id}</p></div>
        <button onClick={() => setModalOpen(true)} className="btn-green"><Plus size={16} /> Add medication</button>
      </div>
      {medsLoading ? <LoadingState label="medications" /> : error ? <ErrorState message={error} onRetry={() => loadMedications(selected.id)} /> : <div>
        {medications.map(m => <div key={m.id} className="border-b border-kBorderSoft">
          <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-4">
            <div><div className="text-sm font-semibold text-kInk">{m.name} {m.dosage && <span className="font-normal text-kMuted">&middot; {m.dosage}</span>}</div><div className="text-xs text-kMuted">{m.schedule || 'No schedule noted'} &middot; since {m.start_date}{m.end_date ? ` – ${m.end_date}` : ''}</div></div>
            <select value={m.status} onChange={e => setStatus(m, e.target.value)} className="rounded-xl border border-kBorder bg-kSurface px-3 py-2 text-xs font-bold text-kInk">{STATUSES.map(s => <option key={s}>{s}</option>)}</select>
          </div>
          <AdministrationLog medication={m} showToast={showToast} />
        </div>)}
        {medications.length === 0 && <p className="px-5 py-10 text-center text-sm text-kMuted">No medications on record.</p>}
      </div>}
    </div>}

    {modalOpen && <Modal title={`Add medication — ${selected.full_name}`} onClose={() => setModalOpen(false)}>
      <form onSubmit={save} className="grid gap-4">
        <label className="text-sm font-semibold">Medication name<input name="name" className="input-k mt-2" required /></label>
        <div className="grid grid-cols-2 gap-4">
          <label className="text-sm font-semibold">Dosage<input name="dosage" className="input-k mt-2" placeholder="e.g. 5mg" /></label>
          <label className="text-sm font-semibold">Schedule<input name="schedule" className="input-k mt-2" placeholder="e.g. Twice daily" /></label>
        </div>
        <label className="text-sm font-semibold">Instructions<textarea name="instructions" rows={2} className="input-k mt-2" placeholder="e.g. Take with food" /></label>
        <div className="grid grid-cols-2 gap-4">
          <label className="text-sm font-semibold">Start date<input name="start_date" type="date" className="input-k mt-2" /></label>
          <label className="text-sm font-semibold">End date<input name="end_date" type="date" className="input-k mt-2" /></label>
        </div>
        <label className="text-sm font-semibold">Notes<textarea name="notes" rows={2} className="input-k mt-2" /></label>
        <button disabled={saving} className="btn-orange mt-2 disabled:opacity-60">{saving ? 'Saving…' : 'Add medication'}</button>
      </form>
    </Modal>}
  </Shell>
}
