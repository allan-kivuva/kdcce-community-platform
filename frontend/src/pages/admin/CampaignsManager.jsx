import { useState, useEffect } from 'react'
import { Plus, Target } from 'lucide-react'
import Shell from '../../components/admin/Shell'
import Modal from '../../components/admin/Modal'
import StatusBadge from '../../components/admin/StatusBadge'
import { LoadingState, ErrorState, EmptyState, errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch } from '../../lib/api'
import { useApiResource } from '../../lib/useApiResource'

const STATUSES = ['Draft', 'Active', 'Paused', 'Completed', 'Archived']

function fmtMoney(n) { return `KES ${Number(n || 0).toLocaleString()}` }

function ProgressBar({ percent }) {
  const pct = Math.min(percent ?? 0, 100)
  return <div className="h-2.5 w-full overflow-hidden rounded-full bg-kBorderSoft"><div className="h-full rounded-full bg-kGreen" style={{ width: `${pct}%` }} /></div>
}

function CampaignFormModal({ campaign, onClose, onSaved, showToast }) {
  const [saving, setSaving] = useState(false)
  const [programs, setPrograms] = useState([])
  const isEdit = !!campaign

  useEffect(() => { apiFetch('/api/programs').then(d => setPrograms(d.programs)).catch(() => {}) }, [])

  async function save(e) {
    e.preventDefault()
    const f = new FormData(e.target)
    setSaving(true)
    try {
      const body = {
        name: f.get('name'), description: f.get('description') || null,
        goal_amount: Number(f.get('goal_amount')), status: f.get('status'),
        program_id: f.get('program_id') ? Number(f.get('program_id')) : null,
        start_date: f.get('start_date') || null, end_date: f.get('end_date') || null,
        public_visible: f.get('public_visible') === 'on',
      }
      if (isEdit) await apiFetch(`/api/admin/campaigns/${campaign.id}`, { method: 'PATCH', body })
      else await apiFetch('/api/admin/campaigns', { method: 'POST', body })
      showToast(isEdit ? 'Campaign updated' : 'Campaign created')
      onSaved()
      onClose()
    } catch (err) { showToast(errorMessage(err)) }
    finally { setSaving(false) }
  }

  return <Modal title={isEdit ? 'Edit campaign' : 'New campaign'} onClose={onClose} wide>
    <form onSubmit={save} className="grid gap-4">
      <label className="text-sm font-semibold">Name<input name="name" defaultValue={campaign?.name} className="input-k mt-2" required /></label>
      <label className="text-sm font-semibold">Description<textarea name="description" defaultValue={campaign?.description} rows={2} className="input-k mt-2" /></label>
      <div className="grid grid-cols-2 gap-4">
        <label className="text-sm font-semibold">Goal amount (KES)<input name="goal_amount" type="number" min="1" step="0.01" defaultValue={campaign?.goal_amount} className="input-k mt-2" required /></label>
        <label className="text-sm font-semibold">Status<select name="status" defaultValue={campaign?.status || 'Draft'} className="input-k mt-2">{STATUSES.map(s => <option key={s}>{s}</option>)}</select></label>
      </div>
      <label className="text-sm font-semibold">Program (optional)<select name="program_id" defaultValue={campaign?.program_id || ''} className="input-k mt-2"><option value="">No program</option>{programs.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
      <div className="grid grid-cols-2 gap-4">
        <label className="text-sm font-semibold">Start date<input name="start_date" type="date" defaultValue={campaign?.start_date} className="input-k mt-2" /></label>
        <label className="text-sm font-semibold">End date<input name="end_date" type="date" defaultValue={campaign?.end_date} className="input-k mt-2" /></label>
      </div>
      <label className="flex items-center gap-2 text-sm font-semibold"><input name="public_visible" type="checkbox" defaultChecked={campaign?.public_visible} className="h-4 w-4" /> Show on the public website (when Active or Completed)</label>
      <button disabled={saving} className="btn-orange mt-2 disabled:opacity-60">{saving ? 'Saving…' : isEdit ? 'Save changes' : 'Create campaign'}</button>
    </form>
  </Modal>
}

function CampaignDetailModal({ campaignId, onClose, onSaved, showToast }) {
  const [campaign, setCampaign] = useState(null)
  const [linking, setLinking] = useState(false)

  const load = () => apiFetch(`/api/admin/campaigns/${campaignId}`).then(d => setCampaign(d.campaign)).catch(err => showToast(errorMessage(err)))
  useEffect(() => { load() }, [campaignId]) // eslint-disable-line react-hooks/exhaustive-deps

  async function linkDonations() {
    setLinking(true)
    try { const res = await apiFetch(`/api/admin/campaigns/${campaignId}/link-donations`, { method: 'POST' }); showToast(`Linked ${res.linked_count} matching donation(s)`); load(); onSaved() }
    catch (err) { showToast(errorMessage(err)) }
    finally { setLinking(false) }
  }

  if (!campaign) return <Modal title="Campaign details" onClose={onClose}><p className="text-sm text-kMuted">Loading…</p></Modal>
  const p = campaign.progress

  return <Modal title="Campaign details" onClose={onClose} wide>
    <div className="-mt-2 mb-4">
      <div className="flex items-center gap-2"><span className="font-display text-lg font-bold text-kGreen">{campaign.name}</span><StatusBadge value={campaign.status} /></div>
      {campaign.program_name && <div className="text-xs font-bold text-kOrange">{campaign.program_name}</div>}
      {campaign.description && <p className="mt-2 text-sm text-kInk">{campaign.description}</p>}
    </div>

    <div className="rounded-xl bg-kCream p-4">
      <div className="flex items-baseline justify-between"><span className="font-display text-xl font-bold text-kGreen">{fmtMoney(p.raised_amount)}</span><span className="text-xs text-kMuted">of {fmtMoney(p.goal_amount)} goal</span></div>
      <div className="mt-2"><ProgressBar percent={p.percent_achieved} /></div>
      <div className="mt-2 flex items-center justify-between text-xs text-kMuted"><span>{p.percent_achieved ?? 0}% complete</span><span>{p.donation_count} donation(s) &middot; {fmtMoney(p.remaining_amount)} remaining</span></div>
    </div>

    <div className="mt-4 flex items-center justify-between">
      <div className="text-xs font-bold uppercase tracking-wide text-kMuted">Recent donations</div>
      <button disabled={linking} onClick={linkDonations} className="text-xs font-bold text-kOrange disabled:opacity-60">{linking ? 'Linking…' : 'Link matching free-text donations'}</button>
    </div>
    <div className="mt-2 grid gap-2">
      {p.recent_donations.map(d => <div key={d.id} className="flex items-center justify-between rounded-xl bg-kCream px-3 py-2 text-sm">
        <span className="font-semibold text-kInk">{d.donor_name}</span>
        <span className="text-kMuted">{fmtMoney(d.amount)} &middot; {new Date(d.created_at).toLocaleDateString([], { dateStyle: 'medium' })}</span>
      </div>)}
      {p.recent_donations.length === 0 && <p className="text-sm text-kMuted">No donations linked to this campaign yet.</p>}
    </div>
  </Modal>
}

export default function CampaignsManager({ showToast }) {
  const campaignsApi = useApiResource('/api/admin/campaigns', { listKey: 'campaigns', itemKey: 'campaign' })
  const [formOpen, setFormOpen] = useState(null)
  const [viewingId, setViewingId] = useState(null)

  return <Shell>
    <div className="flex items-center justify-between">
      <div><div className="eyebrow">Finance</div><h1 className="font-display text-3xl font-bold text-kGreen">Campaigns</h1></div>
      <button onClick={() => setFormOpen('create')} className="btn-orange"><Plus size={16} /> New campaign</button>
    </div>

    <div className="mt-7">
      {campaignsApi.loading && <LoadingState label="campaigns" />}
      {!campaignsApi.loading && campaignsApi.error && <ErrorState message={campaignsApi.error} onRetry={campaignsApi.reload} />}
      {!campaignsApi.loading && !campaignsApi.error && campaignsApi.items.length === 0 && <EmptyState icon={Target} title="No campaigns yet" message="Create one to start tracking fundraising progress." />}
      {!campaignsApi.loading && !campaignsApi.error && campaignsApi.items.length > 0 && <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {campaignsApi.items.map(c => {
          const goal = c.goal_amount || 1
          return <button key={c.id} onClick={() => setViewingId(c.id)} className="card-k p-5 text-left hover:border-kOrange">
            <div className="flex items-center justify-between gap-2"><span className="font-semibold text-kInk">{c.name}</span><StatusBadge value={c.status} /></div>
            {c.program_name && <div className="mt-1 text-xs font-bold text-kOrange">{c.program_name}</div>}
            <div className="mt-4 text-sm font-bold text-kGreen">{fmtMoney(c.progress?.raised_amount)}<span className="ml-1 text-xs font-normal text-kMuted">of {fmtMoney(goal)}</span></div>
            <div className="mt-2"><ProgressBar percent={c.progress?.percent_achieved} /></div>
            <div className="mt-2 flex items-center justify-between text-xs text-kMuted"><span>{c.progress?.percent_achieved ?? 0}%</span><button onClick={e => { e.stopPropagation(); setFormOpen(c) }} className="font-bold text-kOrange">Edit</button></div>
          </button>
        })}
      </div>}
    </div>

    {formOpen && <CampaignFormModal campaign={formOpen === 'create' ? null : formOpen} onClose={() => setFormOpen(null)} onSaved={campaignsApi.reload} showToast={showToast} />}
    {viewingId && <CampaignDetailModal campaignId={viewingId} onClose={() => setViewingId(null)} onSaved={campaignsApi.reload} showToast={showToast} />}
  </Shell>
}
