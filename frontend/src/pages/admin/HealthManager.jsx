import { useState, useEffect, useCallback } from 'react'
import { Search, Plus, AlertTriangle } from 'lucide-react'
import Shell from '../../components/admin/Shell'
import Modal from '../../components/admin/Modal'
import { LoadingState, ErrorState, errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch } from '../../lib/api'

const WELLBEING = ['Good', 'Fair', 'Poor']

function fmt(iso) { return new Date(iso).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }) }

export default function HealthManager({ showToast }) {
  const [members, setMembers] = useState([])
  const [membersLoading, setMembersLoading] = useState(true)
  const [followUps, setFollowUps] = useState([])
  const [q, setQ] = useState('')
  const [selected, setSelected] = useState(null)
  const [records, setRecords] = useState([])
  const [recordsLoading, setRecordsLoading] = useState(false)
  const [error, setError] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [saving, setSaving] = useState(false)

  const loadMembers = useCallback(async () => {
    setMembersLoading(true)
    try { setMembers((await apiFetch('/api/elderly')).members) }
    catch (err) { setError(errorMessage(err)) }
    finally { setMembersLoading(false) }
  }, [])

  const loadFollowUps = useCallback(async () => {
    try { setFollowUps((await apiFetch('/api/health-records?follow_up_required=true')).records) }
    catch { /* shown via the main error state if members also fail */ }
  }, [])

  useEffect(() => { loadMembers(); loadFollowUps() }, [loadMembers, loadFollowUps])

  const loadRecords = useCallback(async (memberId) => {
    setRecordsLoading(true)
    setError('')
    try { setRecords((await apiFetch(`/api/health-records?elderly_member_id=${memberId}`)).records) }
    catch (err) { setError(errorMessage(err)) }
    finally { setRecordsLoading(false) }
  }, [])

  function selectMember(m) {
    setSelected(m)
    setQ('')
    loadRecords(m.id)
  }

  const query = q.trim().toLowerCase()
  const results = query
    ? members.filter(m => m.full_name.toLowerCase().includes(query) || m.member_id.toLowerCase().includes(query)).slice(0, 8)
    : []

  async function save(e) {
    e.preventDefault()
    const f = new FormData(e.target)
    const num = key => (f.get(key) ? Number(f.get(key)) : null)
    const data = {
      elderly_member_id: selected.id,
      blood_pressure_systolic: num('blood_pressure_systolic'),
      blood_pressure_diastolic: num('blood_pressure_diastolic'),
      temperature_celsius: num('temperature_celsius'),
      pulse_bpm: num('pulse_bpm'),
      weight_kg: num('weight_kg'),
      wellbeing: f.get('wellbeing') || null,
      mood: f.get('mood') || null,
      physical_activity: f.get('physical_activity') || null,
      observations: f.get('observations') || null,
      follow_up_required: f.get('follow_up_required') === 'on',
      follow_up_notes: f.get('follow_up_notes') || null,
    }
    setSaving(true)
    try {
      await apiFetch('/api/health-records', { method: 'POST', body: data })
      showToast('Observation recorded')
      setModalOpen(false)
      loadRecords(selected.id)
      loadFollowUps()
    } catch (err) { showToast(errorMessage(err)) }
    finally { setSaving(false) }
  }

  return <Shell>
    <div><div className="eyebrow">Manage</div><h1 className="font-display text-3xl font-bold text-kGreen">Health &amp; wellness</h1></div>

    {followUps.length > 0 && <div className="card-k mt-7 border-l-4 border-l-kOrange p-5">
      <div className="flex items-center gap-2 text-kOrange"><AlertTriangle size={18} /><h2 className="font-display text-lg font-bold">Needs follow-up ({followUps.length})</h2></div>
      <div className="mt-3 grid gap-2">
        {followUps.map(r => <button key={r.id} onClick={() => { const m = members.find(x => x.id === r.elderly_member_id); if (m) selectMember(m) }} className="flex items-center justify-between rounded-xl border border-kBorder px-4 py-2 text-left text-sm hover:bg-kCream">
          <span className="font-semibold text-kInk">{r.elderly_member_name} <span className="font-normal text-kMuted">({r.elderly_member_code})</span></span>
          <span className="text-kMuted">{fmt(r.recorded_at)}</span>
        </button>)}
      </div>
    </div>}

    <div className="card-k mt-6 p-6">
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
        <button onClick={() => setModalOpen(true)} className="btn-green"><Plus size={16} /> Record observation</button>
      </div>
      {recordsLoading ? <LoadingState label="observations" /> : error ? <ErrorState message={error} onRetry={() => loadRecords(selected.id)} /> : <div className="overflow-x-auto"><table className="w-full min-w-[800px] text-left text-sm"><thead className="bg-kBorderSoft text-xs uppercase tracking-wider text-kMuted"><tr><th className="px-5 py-4">Date</th><th className="px-5 py-4">BP</th><th className="px-5 py-4">Pulse</th><th className="px-5 py-4">Temp</th><th className="px-5 py-4">Weight</th><th className="px-5 py-4">Wellbeing</th><th className="px-5 py-4">Follow-up</th></tr></thead><tbody>
        {records.map(r => <tr key={r.id} className="border-b border-kBorderSoft"><td className="px-5 py-4 text-kMuted">{fmt(r.recorded_at)}</td><td className="px-5 py-4 text-kMuted">{r.blood_pressure_systolic ? `${r.blood_pressure_systolic}/${r.blood_pressure_diastolic}` : '—'}</td><td className="px-5 py-4 text-kMuted">{r.pulse_bpm ?? '—'}</td><td className="px-5 py-4 text-kMuted">{r.temperature_celsius ?? '—'}</td><td className="px-5 py-4 text-kMuted">{r.weight_kg ?? '—'}</td><td className="px-5 py-4 text-kMuted">{r.wellbeing ?? '—'}</td><td className="px-5 py-4">{r.follow_up_required ? <span className="rounded-full bg-kTint px-3 py-1 text-xs font-bold text-kOrange">Required</span> : '—'}</td></tr>)}
        {records.length === 0 && <tr><td colSpan={7} className="px-5 py-10 text-center text-sm text-kMuted">No observations recorded yet.</td></tr>}
      </tbody></table></div>}
    </div>}

    {modalOpen && <Modal title={`Record observation — ${selected.full_name}`} onClose={() => setModalOpen(false)}>
      <form onSubmit={save} className="grid gap-4">
        <div className="grid grid-cols-2 gap-4">
          <label className="text-sm font-semibold">BP systolic<input name="blood_pressure_systolic" type="number" className="input-k mt-2" /></label>
          <label className="text-sm font-semibold">BP diastolic<input name="blood_pressure_diastolic" type="number" className="input-k mt-2" /></label>
        </div>
        <div className="grid grid-cols-3 gap-4">
          <label className="text-sm font-semibold">Pulse (bpm)<input name="pulse_bpm" type="number" className="input-k mt-2" /></label>
          <label className="text-sm font-semibold">Temp (&deg;C)<input name="temperature_celsius" type="number" step="0.1" className="input-k mt-2" /></label>
          <label className="text-sm font-semibold">Weight (kg)<input name="weight_kg" type="number" step="0.1" className="input-k mt-2" /></label>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <label className="text-sm font-semibold">Wellbeing<select name="wellbeing" defaultValue="" className="input-k mt-2"><option value="">Not noted</option>{WELLBEING.map(w => <option key={w}>{w}</option>)}</select></label>
          <label className="text-sm font-semibold">Mood<input name="mood" className="input-k mt-2" placeholder="e.g. Cheerful" /></label>
        </div>
        <label className="text-sm font-semibold">Physical activity<textarea name="physical_activity" rows={2} className="input-k mt-2" placeholder="e.g. Walked 20 minutes with support" /></label>
        <label className="text-sm font-semibold">Health observations<textarea name="observations" rows={2} className="input-k mt-2" /></label>
        <label className="flex items-center gap-2 text-sm font-semibold"><input name="follow_up_required" type="checkbox" className="h-5 w-5" /> Follow-up required</label>
        <label className="text-sm font-semibold">Follow-up notes<textarea name="follow_up_notes" rows={2} className="input-k mt-2" /></label>
        <button disabled={saving} className="btn-orange mt-2 disabled:opacity-60">{saving ? 'Saving…' : 'Record observation'}</button>
      </form>
    </Modal>}
  </Shell>
}
