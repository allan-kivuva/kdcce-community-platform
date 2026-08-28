import { useState, useEffect, useCallback } from 'react'
import { Search, Plus, Users } from 'lucide-react'
import Shell from '../../components/admin/Shell'
import Modal from '../../components/admin/Modal'
import { LoadingState, ErrorState, errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch } from '../../lib/api'

const MEAL_TYPES = ['Breakfast', 'Lunch', 'Snack', 'Special']

function todayIso() { return new Date().toISOString().slice(0, 10) }

function NewMealModal({ onClose, onCreated, showToast }) {
  const [saving, setSaving] = useState(false)
  async function save(e) {
    e.preventDefault()
    const f = new FormData(e.target)
    setSaving(true)
    try {
      await onCreated({ meal_type: f.get('meal_type'), meal_date: f.get('meal_date'), description: f.get('description') || null })
      showToast('Meal planned')
      onClose()
    } catch (err) { showToast(errorMessage(err)) }
    finally { setSaving(false) }
  }
  return <Modal title="Plan a meal" onClose={onClose}>
    <form onSubmit={save} className="grid gap-4">
      <div className="grid grid-cols-2 gap-4">
        <label className="text-sm font-semibold">Meal type<select name="meal_type" defaultValue="Lunch" className="input-k mt-2">{MEAL_TYPES.map(t => <option key={t}>{t}</option>)}</select></label>
        <label className="text-sm font-semibold">Date<input name="meal_date" type="date" defaultValue={todayIso()} className="input-k mt-2" required /></label>
      </div>
      <label className="text-sm font-semibold">Menu / description<textarea name="description" rows={2} className="input-k mt-2" placeholder="e.g. Ugali, sukuma wiki, beans" /></label>
      <button disabled={saving} className="btn-orange mt-2 disabled:opacity-60">{saving ? 'Saving…' : 'Plan meal'}</button>
    </form>
  </Modal>
}

function AttendancePanel({ meal, onAttendanceChanged, showToast }) {
  const [members, setMembers] = useState([])
  const [attendance, setAttendance] = useState([])
  const [loading, setLoading] = useState(true)
  const [q, setQ] = useState('')
  const [busyId, setBusyId] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [membersRes, attendanceRes] = await Promise.all([
        apiFetch('/api/elderly'),
        apiFetch(`/api/meals/${meal.id}/attendance`),
      ])
      setMembers(membersRes.members)
      setAttendance(attendanceRes.attendance)
    } catch (err) { showToast(errorMessage(err)) }
    finally { setLoading(false) }
  }, [meal.id, showToast])

  useEffect(() => { load() }, [load])

  const attendedIds = new Set(attendance.map(a => a.elderly_member_id))
  const query = q.trim().toLowerCase()
  const results = query
    ? members.filter(m => !attendedIds.has(m.id) && (m.full_name.toLowerCase().includes(query) || m.member_id.toLowerCase().includes(query))).slice(0, 8)
    : []

  async function mark(member) {
    setBusyId(member.id)
    try {
      await apiFetch(`/api/meals/${meal.id}/attendance`, { method: 'POST', body: { elderly_member_id: member.id } })
      showToast(`${member.full_name} marked present`)
      setQ('')
      load()
      onAttendanceChanged()
    } catch (err) { showToast(errorMessage(err)) }
    finally { setBusyId(null) }
  }

  return <div className="card-k mt-6 p-6">
    <div className="flex items-center justify-between"><h2 className="font-display text-lg font-bold text-kGreen">{meal.meal_type} &middot; {meal.meal_date}</h2><div className="flex items-center gap-2 text-sm font-semibold text-kMuted"><Users size={16} /> {attendance.length} attended</div></div>
    {meal.description && <p className="mt-2 text-sm text-kMuted">{meal.description}</p>}

    <div className="relative mt-5"><Search className="absolute left-3 top-3.5 text-kMuted" size={17} /><input value={q} onChange={e => setQ(e.target.value)} className="input-k pl-10" placeholder="Search a member to mark present..." /></div>
    {query && <div className="mt-3 grid gap-2">
      {results.length === 0 && <p className="text-sm text-kMuted">No matching member.</p>}
      {results.map(m => <div key={m.id} className="flex items-center justify-between rounded-xl border border-kBorder px-4 py-3">
        <div><div className="text-sm font-semibold text-kInk">{m.full_name}</div><div className="text-xs text-kMuted">{m.member_id}{m.allergies ? ` · Allergies: ${m.allergies}` : ''}{m.dietary_requirements ? ` · Diet: ${m.dietary_requirements}` : ''}</div></div>
        <button disabled={busyId === m.id} onClick={() => mark(m)} className="btn-green disabled:opacity-60">Mark present</button>
      </div>)}
    </div>}

    {loading ? <p className="mt-4 text-sm text-kMuted">Loading attendance…</p> : <ul className="mt-5 grid gap-2 text-sm">
      {attendance.map(a => <li key={a.id} className="rounded-xl bg-kCream px-4 py-2"><span className="font-semibold text-kInk">{a.elderly_member_name}</span> <span className="text-kMuted">({a.elderly_member_code})</span></li>)}
      {attendance.length === 0 && <li className="text-kMuted">No one marked present yet.</li>}
    </ul>}
  </div>
}

export default function FeedingManager({ showToast }) {
  const [meals, setMeals] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [date, setDate] = useState(todayIso())
  const [typeFilter, setTypeFilter] = useState('All')
  const [selected, setSelected] = useState(null)
  const [newModalOpen, setNewModalOpen] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const params = new URLSearchParams()
      if (date) params.set('date', date)
      if (typeFilter !== 'All') params.set('meal_type', typeFilter)
      const data = await apiFetch(`/api/meals?${params.toString()}`)
      setMeals(data.meals)
      setSelected(prev => prev ? data.meals.find(m => m.id === prev.id) || null : null)
    } catch (err) { setError(errorMessage(err)) }
    finally { setLoading(false) }
  }, [date, typeFilter])

  useEffect(() => { load() }, [load])

  return <Shell>
    <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
      <div><div className="eyebrow">Manage</div><h1 className="font-display text-3xl font-bold text-kGreen">Feeding</h1></div>
      <button onClick={() => setNewModalOpen(true)} className="btn-green"><Plus size={16} /> Plan meal</button>
    </div>

    <div className="mt-7 grid gap-6 xl:grid-cols-[1fr_1.1fr]">
      <div>
        <div className="card-k overflow-hidden">
          <div className="flex flex-col gap-3 border-b border-kBorderSoft p-5 sm:flex-row">
            <input type="date" value={date} onChange={e => setDate(e.target.value)} className="input-k" />
            <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)} className="rounded-xl border border-kBorder bg-kSurface px-4 py-3 text-sm text-kInk"><option>All</option>{MEAL_TYPES.map(t => <option key={t}>{t}</option>)}</select>
          </div>
          {loading ? <LoadingState label="meals" /> : error ? <ErrorState message={error} onRetry={load} /> : <div className="grid gap-2 p-4">
            {meals.map(m => <button key={m.id} onClick={() => setSelected(m)} className={`flex items-center justify-between rounded-xl border px-4 py-3 text-left ${selected?.id === m.id ? 'border-kOrange bg-kTint' : 'border-kBorder hover:bg-kCream'}`}>
              <div><div className="font-semibold text-kInk">{m.meal_type}</div><div className="text-xs text-kMuted">{m.meal_date}{m.description ? ` · ${m.description}` : ''}</div></div>
              <div className="flex items-center gap-1 text-xs font-bold text-kOrange"><Users size={14} /> {m.attendee_count}</div>
            </button>)}
            {meals.length === 0 && <p className="p-4 text-center text-sm text-kMuted">No meals planned for this filter.</p>}
          </div>}
        </div>
      </div>
      <div>{selected ? <AttendancePanel meal={selected} onAttendanceChanged={load} showToast={showToast} /> : <div className="card-k p-10 text-center text-sm text-kMuted">Select a meal to record attendance.</div>}</div>
    </div>

    {newModalOpen && <NewMealModal onClose={() => setNewModalOpen(false)} onCreated={async data => { await apiFetch('/api/meals', { method: 'POST', body: data }); load() }} showToast={showToast} />}
  </Shell>
}
