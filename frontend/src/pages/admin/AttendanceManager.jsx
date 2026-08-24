import { useState, useEffect, useCallback } from 'react'
import { Search, LogIn, LogOut, Clock } from 'lucide-react'
import Shell from '../../components/admin/Shell'
import { LoadingState, ErrorState, errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch } from '../../lib/api'

function todayIso() { return new Date().toISOString().slice(0, 10) }
function timeOf(iso) { return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }

export default function AttendanceManager({ showToast }) {
  const [members, setMembers] = useState([])
  const [membersLoading, setMembersLoading] = useState(true)
  const [today, setToday] = useState([])
  const [todayLoading, setTodayLoading] = useState(true)
  const [error, setError] = useState('')
  const [q, setQ] = useState('')
  const [busyId, setBusyId] = useState(null)

  const loadMembers = useCallback(async () => {
    setMembersLoading(true)
    try { setMembers((await apiFetch('/api/elderly')).members) }
    catch (err) { setError(errorMessage(err)) }
    finally { setMembersLoading(false) }
  }, [])

  const loadToday = useCallback(async () => {
    setTodayLoading(true)
    setError('')
    try { setToday((await apiFetch(`/api/attendance?date=${todayIso()}`)).attendance) }
    catch (err) { setError(errorMessage(err)) }
    finally { setTodayLoading(false) }
  }, [])

  useEffect(() => { loadMembers(); loadToday() }, [loadMembers, loadToday])

  const checkedInIds = new Set(today.filter(r => !r.check_out_at).map(r => r.elderly_member_id))
  const query = q.trim().toLowerCase()
  const results = query
    ? members.filter(m => m.full_name.toLowerCase().includes(query) || m.member_id.toLowerCase().includes(query)).slice(0, 8)
    : []

  async function checkIn(member) {
    setBusyId(member.id)
    try {
      await apiFetch('/api/attendance/check-in', { method: 'POST', body: { elderly_member_id: member.id } })
      showToast(`${member.full_name} checked in`)
      setQ('')
      loadToday()
    } catch (err) { showToast(errorMessage(err)) }
    finally { setBusyId(null) }
  }

  async function checkOut(record) {
    setBusyId(record.id)
    try {
      await apiFetch(`/api/attendance/${record.id}/check-out`, { method: 'PATCH', body: {} })
      showToast(`${record.elderly_member_name} checked out`)
      loadToday()
    } catch (err) { showToast(errorMessage(err)) }
    finally { setBusyId(null) }
  }

  return <Shell>
    <div><div className="eyebrow">Manage</div><h1 className="font-display text-3xl font-bold text-kGreen">Attendance</h1></div>

    <div className="card-k mt-7 p-6">
      <h2 className="font-display text-lg font-bold text-kGreen">Check in a member</h2>
      <div className="relative mt-4"><Search className="absolute left-3 top-3.5 text-kMuted" size={17} /><input value={q} onChange={e => setQ(e.target.value)} className="input-k pl-10" placeholder="Search by name or member ID..." /></div>
      {membersLoading ? <p className="mt-3 text-sm text-kMuted">Loading members…</p> : query && <div className="mt-3 grid gap-2">
        {results.length === 0 && <p className="text-sm text-kMuted">No matching member.</p>}
        {results.map(m => {
          const already = checkedInIds.has(m.id)
          return <div key={m.id} className="flex items-center justify-between rounded-xl border border-kBorder px-4 py-3">
            <div><div className="text-sm font-semibold text-kInk">{m.full_name}</div><div className="text-xs text-kMuted">{m.member_id} &middot; {m.gender}{m.opa_name ? ` · ${m.opa_name}` : ''}</div></div>
            {already
              ? <span className="text-xs font-semibold text-kMuted">Already checked in</span>
              : <button disabled={busyId === m.id} onClick={() => checkIn(m)} className="btn-green disabled:opacity-60"><LogIn size={15} /> Check in</button>}
          </div>
        })}
      </div>}
    </div>

    <div className="card-k mt-6 overflow-hidden">
      <div className="flex items-center justify-between border-b border-kBorderSoft p-5"><h2 className="font-display text-lg font-bold text-kGreen">Today</h2><div className="flex items-center gap-2 text-xs font-semibold text-kMuted"><Clock size={14} /> {todayIso()}</div></div>
      {todayLoading ? <LoadingState label="attendance" /> : error ? <ErrorState message={error} onRetry={loadToday} /> : <div className="overflow-x-auto"><table className="w-full min-w-[700px] text-left text-sm"><thead className="bg-kBorderSoft text-xs uppercase tracking-wider text-kMuted"><tr><th className="px-5 py-4">Member</th><th className="px-5 py-4">Check-in</th><th className="px-5 py-4">Check-out</th><th className="px-5 py-4">Recorded by</th><th className="px-5 py-4">Actions</th></tr></thead><tbody>
        {today.map(r => <tr key={r.id} className="border-b border-kBorderSoft"><td className="px-5 py-4 font-semibold text-kInk">{r.elderly_member_name} <span className="font-normal text-kMuted">({r.elderly_member_code})</span></td><td className="px-5 py-4 text-kMuted">{timeOf(r.check_in_at)}</td><td className="px-5 py-4 text-kMuted">{r.check_out_at ? timeOf(r.check_out_at) : '—'}</td><td className="px-5 py-4 text-kMuted">{r.recorded_by}</td><td className="px-5 py-4">{!r.check_out_at && <button disabled={busyId === r.id} onClick={() => checkOut(r)} className="flex items-center gap-1 text-sm font-semibold text-kOrange disabled:opacity-60"><LogOut size={16} /> Check out</button>}</td></tr>)}
        {today.length === 0 && <tr><td colSpan={5} className="px-5 py-10 text-center text-sm text-kMuted">No check-ins yet today.</td></tr>}
      </tbody></table></div>}
    </div>
  </Shell>
}
