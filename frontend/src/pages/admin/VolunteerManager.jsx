import { useState } from 'react'
import { Search, Check, X as XIcon } from 'lucide-react'
import Shell from '../../components/admin/Shell'
import { LoadingState, ErrorState, errorMessage } from '../../components/admin/adminHelpers'
import { useApiResource } from '../../lib/useApiResource'

const STATUS_STYLES = {
  Pending: 'bg-kTint text-kOrange',
  Verified: 'bg-kGreen/10 text-kGreen',
  Rejected: 'bg-red-100 text-red-700',
}

export default function VolunteerManager({ showToast }) {
  const volunteersApi = useApiResource('/api/volunteers', { listKey: 'volunteers', itemKey: 'volunteer' })
  const [q, setQ] = useState('')
  const [statusFilter, setStatusFilter] = useState('All')

  const filtered = volunteersApi.items.filter(v =>
    (statusFilter === 'All' || v.status === statusFilter) &&
    (v.name.toLowerCase().includes(q.toLowerCase()) || v.email.toLowerCase().includes(q.toLowerCase()))
  )

  async function setStatus(volunteer, status) {
    try {
      await volunteersApi.patch(volunteer.id, { status })
      showToast(`${volunteer.name} marked ${status}`)
    } catch (err) { showToast(errorMessage(err)) }
  }

  return <Shell>
    <div><div className="eyebrow">Manage</div><h1 className="font-display text-3xl font-bold text-kGreen">Volunteers</h1></div>

    {volunteersApi.loading ? <LoadingState label="volunteers" /> : volunteersApi.error ? <ErrorState message={volunteersApi.error} onRetry={volunteersApi.reload} /> : <div className="card-k mt-7 overflow-hidden">
      <div className="flex flex-col gap-3 border-b border-kBorderSoft p-5 sm:flex-row">
        <div className="relative flex-1"><Search className="absolute left-3 top-3.5 text-kMuted" size={17} /><input value={q} onChange={e => setQ(e.target.value)} className="input-k pl-10" placeholder="Search name or email..." /></div>
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="rounded-xl border border-kBorder bg-kSurface px-4 py-3 text-sm text-kInk"><option>All</option><option>Pending</option><option>Verified</option><option>Rejected</option></select>
      </div>
      <div className="overflow-x-auto"><table className="w-full min-w-[800px] text-left text-sm"><thead className="bg-kBorderSoft text-xs uppercase tracking-wider text-kMuted"><tr><th className="px-5 py-4">Name</th><th className="px-5 py-4">Contact</th><th className="px-5 py-4">Skills</th><th className="px-5 py-4">Availability</th><th className="px-5 py-4">Status</th><th className="px-5 py-4">Actions</th></tr></thead><tbody>
        {filtered.map(v => <tr key={v.id} className="border-b border-kBorderSoft"><td className="px-5 py-4 font-semibold text-kInk">{v.name}</td><td className="px-5 py-4 text-kMuted">{v.email}{v.phone ? ` · ${v.phone}` : ''}</td><td className="px-5 py-4 text-kMuted">{v.skills || '—'}</td><td className="px-5 py-4 text-kMuted">{v.availability || '—'}</td><td className="px-5 py-4"><span className={`rounded-full px-3 py-1 text-xs font-bold ${STATUS_STYLES[v.status]}`}>{v.status}</span></td><td className="px-5 py-4">{v.status === 'Pending' && <div className="flex gap-2">
          <button onClick={() => setStatus(v, 'Verified')} className="flex items-center gap-1 rounded-lg bg-kGreen px-3 py-1.5 text-xs font-bold text-white"><Check size={14} /> Verify</button>
          <button onClick={() => setStatus(v, 'Rejected')} className="flex items-center gap-1 rounded-lg border border-kBorder px-3 py-1.5 text-xs font-bold text-kMuted"><XIcon size={14} /> Reject</button>
        </div>}{v.status !== 'Pending' && <button onClick={() => setStatus(v, v.status === 'Verified' ? 'Rejected' : 'Verified')} className="text-xs font-semibold text-kOrange">{v.status === 'Verified' ? 'Revoke' : 'Verify instead'}</button>}</td></tr>)}
        {filtered.length === 0 && <tr><td colSpan={6} className="px-5 py-10 text-center text-sm text-kMuted">No volunteers match your search.</td></tr>}
      </tbody></table></div>
    </div>}
  </Shell>
}
