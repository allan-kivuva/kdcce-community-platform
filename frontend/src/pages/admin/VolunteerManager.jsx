import { useState } from 'react'
import { Search, Check, X as XIcon } from 'lucide-react'
import Shell from '../../components/admin/Shell'
import Modal from '../../components/admin/Modal'
import { LoadingState, ErrorState, errorMessage } from '../../components/admin/adminHelpers'
import { useApiResource } from '../../lib/useApiResource'

const STATUS_STYLES = {
  Pending: 'bg-kTint text-kOrange',
  Verified: 'bg-kGreen/10 text-kGreen',
  Rejected: 'bg-red-100 text-red-700',
}

function Field({ label, value }) {
  if (!value) return null
  return <div><div className="text-xs font-bold uppercase tracking-wide text-kMuted">{label}</div><p className="mt-1 text-sm leading-6 text-kInk">{value}</p></div>
}

function ReviewModal({ volunteer, onClose, onDecide, showToast }) {
  const [rejecting, setRejecting] = useState(false)
  const [reason, setReason] = useState('')
  const [saving, setSaving] = useState(false)

  async function approve() {
    if (!window.confirm(`Approve ${volunteer.name} as a volunteer? They will immediately gain access to the volunteer portal.`)) return
    setSaving(true)
    try {
      await onDecide(volunteer.id, { status: 'Verified' })
      showToast(`${volunteer.name} approved`)
      onClose()
    } catch (err) { showToast(errorMessage(err)) }
    finally { setSaving(false) }
  }

  async function reject() {
    if (!window.confirm(`Reject ${volunteer.name}'s application? They will not gain volunteer portal access.`)) return
    setSaving(true)
    try {
      await onDecide(volunteer.id, { status: 'Rejected', rejection_reason: reason || null })
      showToast(`${volunteer.name} rejected`)
      onClose()
    } catch (err) { showToast(errorMessage(err)) }
    finally { setSaving(false) }
  }

  return <Modal title="Volunteer application" onClose={onClose}>
    <div className="grid gap-4">
      <div className="flex items-center justify-between"><div><div className="font-display text-lg font-bold text-kGreen">{volunteer.name}</div><div className="text-sm text-kMuted">{volunteer.email}{volunteer.phone ? ` · ${volunteer.phone}` : ''}</div></div><span className={`rounded-full px-3 py-1 text-xs font-bold ${STATUS_STYLES[volunteer.status]}`}>{volunteer.status}</span></div>

      <Field label="Skills" value={volunteer.skills} />
      <Field label="Availability" value={volunteer.availability} />
      <Field label="Areas of interest" value={volunteer.areas_of_interest} />
      <Field label="Experience" value={volunteer.experience} />
      <Field label="Motivation" value={volunteer.motivation} />
      <Field label="About" value={volunteer.bio} />
      {volunteer.rejection_reason && <div className="rounded-xl bg-red-50 p-3"><Field label="Rejection reason on file" value={volunteer.rejection_reason} /></div>}
      {volunteer.reviewed_by && <p className="text-xs text-kMuted">Last reviewed by {volunteer.reviewed_by} on {new Date(volunteer.reviewed_at).toLocaleDateString()}</p>}

      {volunteer.status === 'Pending' && <div className="mt-2 grid gap-3 border-t border-kBorderSoft pt-5">
        {!rejecting ? <div className="flex gap-3">
          <button disabled={saving} onClick={approve} className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-kGreen px-4 py-3 text-sm font-bold text-white disabled:opacity-60"><Check size={16} /> Approve</button>
          <button disabled={saving} onClick={() => setRejecting(true)} className="flex flex-1 items-center justify-center gap-2 rounded-xl border border-kBorder px-4 py-3 text-sm font-bold text-kMuted disabled:opacity-60"><XIcon size={16} /> Reject</button>
        </div> : <>
          <label className="text-sm font-semibold">Reason (optional, shown to the applicant)<textarea value={reason} onChange={e => setReason(e.target.value)} rows={2} className="input-k mt-2" placeholder="e.g. We currently have sufficient volunteers for this area." /></label>
          <div className="flex gap-3"><button disabled={saving} onClick={reject} className="flex-1 rounded-xl bg-red-600 px-4 py-3 text-sm font-bold text-white disabled:opacity-60">{saving ? 'Rejecting…' : 'Confirm rejection'}</button><button onClick={() => setRejecting(false)} className="rounded-xl border border-kBorder px-4 py-3 text-sm font-bold text-kMuted">Back</button></div>
        </>}
      </div>}

      {volunteer.status !== 'Pending' && <div className="mt-2 border-t border-kBorderSoft pt-5"><button disabled={saving} onClick={() => onDecide(volunteer.id, { status: volunteer.status === 'Verified' ? 'Rejected' : 'Verified' }).then(() => { showToast('Status updated'); onClose() }).catch(err => showToast(errorMessage(err)))} className="text-sm font-semibold text-kOrange">{volunteer.status === 'Verified' ? 'Revoke verification' : 'Verify instead'}</button></div>}
    </div>
  </Modal>
}

export default function VolunteerManager({ showToast }) {
  const volunteersApi = useApiResource('/api/volunteers', { listKey: 'volunteers', itemKey: 'volunteer' })
  const [q, setQ] = useState('')
  const [statusFilter, setStatusFilter] = useState('All')
  const [reviewing, setReviewing] = useState(null)

  const filtered = volunteersApi.items.filter(v =>
    (statusFilter === 'All' || v.status === statusFilter) &&
    (v.name.toLowerCase().includes(q.toLowerCase()) || v.email.toLowerCase().includes(q.toLowerCase()))
  )

  return <Shell>
    <div><div className="eyebrow">Manage</div><h1 className="font-display text-3xl font-bold text-kGreen">Volunteer Applications</h1></div>

    {volunteersApi.loading ? <LoadingState label="volunteers" /> : volunteersApi.error ? <ErrorState message={volunteersApi.error} onRetry={volunteersApi.reload} /> : <div className="card-k mt-7 overflow-hidden">
      <div className="flex flex-col gap-3 border-b border-kBorderSoft p-5 sm:flex-row">
        <div className="relative flex-1"><Search className="absolute left-3 top-3.5 text-kMuted" size={17} /><input value={q} onChange={e => setQ(e.target.value)} className="input-k pl-10" placeholder="Search name or email..." /></div>
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="rounded-xl border border-kBorder bg-kSurface px-4 py-3 text-sm text-kInk"><option>All</option><option>Pending</option><option>Verified</option><option>Rejected</option></select>
      </div>
      <div className="overflow-x-auto"><table className="w-full min-w-[800px] text-left text-sm"><thead className="bg-kBorderSoft text-xs uppercase tracking-wider text-kMuted"><tr><th className="px-5 py-4">Name</th><th className="px-5 py-4">Contact</th><th className="px-5 py-4">Skills</th><th className="px-5 py-4">Availability</th><th className="px-5 py-4">Status</th><th className="px-5 py-4">Action</th></tr></thead><tbody>
        {filtered.map(v => <tr key={v.id} className="border-b border-kBorderSoft"><td className="px-5 py-4 font-semibold text-kInk">{v.name}</td><td className="px-5 py-4 text-kMuted">{v.email}{v.phone ? ` · ${v.phone}` : ''}</td><td className="px-5 py-4 text-kMuted">{v.skills || '—'}</td><td className="px-5 py-4 text-kMuted">{v.availability || '—'}</td><td className="px-5 py-4"><span className={`rounded-full px-3 py-1 text-xs font-bold ${STATUS_STYLES[v.status]}`}>{v.status}</span></td><td className="px-5 py-4"><button onClick={() => setReviewing(v)} className="text-xs font-bold text-kOrange">{v.status === 'Pending' ? 'Review' : 'View'}</button></td></tr>)}
        {filtered.length === 0 && <tr><td colSpan={6} className="px-5 py-10 text-center text-sm text-kMuted">No volunteers match your search.</td></tr>}
      </tbody></table></div>
    </div>}

    {reviewing && <ReviewModal volunteer={reviewing} onClose={() => setReviewing(null)} onDecide={(id, data) => volunteersApi.patch(id, data)} showToast={showToast} />}
  </Shell>
}
