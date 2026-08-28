import { useState, useEffect } from 'react'
import { AlertTriangle, CheckCircle2 } from 'lucide-react'
import VolunteerShell from '../../components/volunteer/VolunteerShell'
import { errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch } from '../../lib/api'

const CATEGORIES = ['Medical Concern', 'Safety Concern', 'Welfare Concern', 'Emergency', 'Missing Person', 'Other']
const SEVERITIES = ['Low', 'Medium', 'High', 'Critical']

// Submits to the existing Incident model (see backend/app/incidents —
// IncidentVolunteerCreateSchema) rather than a second reporting system.
// Critical severity triggers the same admin/staff notify() broadcast an
// admin-raised critical incident would. Volunteers cannot list, view, or
// edit incidents afterward — including their own — this is fire-and-forget
// by design (see docs on the "Restricted create only" decision).
export default function ReportConcern({ showToast }) {
  const [members, setMembers] = useState([])
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  useEffect(() => { apiFetch('/api/volunteers/me/elderly-members').then(d => setMembers(d.elderly_members)).catch(() => {}) }, [])

  async function submit(e) {
    e.preventDefault()
    const f = new FormData(e.target)
    const memberVal = f.get('elderly_member_id')
    const data = {
      elderly_member_id: memberVal ? Number(memberVal) : null,
      incident_type: f.get('incident_type'),
      severity: f.get('severity'),
      description: f.get('description'),
      immediate_action_taken: f.get('immediate_action_taken') || null,
      follow_up_required: f.get('follow_up_required') === 'on',
      follow_up_notes: f.get('follow_up_notes') || null,
    }
    setSubmitting(true)
    try {
      await apiFetch('/api/incidents', { method: 'POST', body: data })
      setSubmitted(true)
      showToast('Concern reported to KDCCE staff')
    } catch (err) { showToast(errorMessage(err)) }
    finally { setSubmitting(false) }
  }

  return <VolunteerShell>
    <div><div className="eyebrow">Safeguarding</div><h1 className="font-display text-3xl font-bold text-kGreen">Report a Concern</h1></div>
    <p className="mt-2 max-w-xl text-sm leading-6 text-kMuted">Raise a medical, safety, welfare or other concern directly with KDCCE staff. Critical concerns notify staff immediately.</p>

    {submitted ? <div className="card-k mt-7 p-9 text-center"><div className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-kGreen/10 text-kGreen"><CheckCircle2 /></div><h2 className="mt-4 font-display text-xl font-bold text-kGreen">Concern reported</h2><p className="mt-2 text-sm text-kMuted">KDCCE staff have been notified and will follow up as needed.</p><button onClick={() => setSubmitted(false)} className="btn-orange mt-6">Report another concern</button></div> : <form onSubmit={submit} className="card-k mt-7 grid gap-4 p-6">
      <label className="text-sm font-semibold">Elderly member (if applicable)<select name="elderly_member_id" defaultValue="" className="input-k mt-2"><option value="">General concern — not about a specific member</option>{members.map(m => <option key={m.id} value={m.id}>{m.full_name} ({m.member_id})</option>)}</select></label>
      <div className="grid grid-cols-2 gap-4">
        <label className="text-sm font-semibold">Category<select name="incident_type" defaultValue={CATEGORIES[0]} className="input-k mt-2">{CATEGORIES.map(c => <option key={c}>{c}</option>)}</select></label>
        <label className="text-sm font-semibold">Severity<select name="severity" defaultValue="Medium" className="input-k mt-2">{SEVERITIES.map(s => <option key={s}>{s}</option>)}</select></label>
      </div>
      <label className="text-sm font-semibold">Description<textarea name="description" rows={4} className="input-k mt-2" placeholder="What happened, and any relevant detail" required /></label>
      <label className="text-sm font-semibold">Additional details (optional)<textarea name="immediate_action_taken" rows={2} className="input-k mt-2" placeholder="Anything else that could help staff respond" /></label>
      <label className="flex items-center gap-2 text-sm font-semibold"><input type="checkbox" name="follow_up_required" className="h-5 w-5" /> Follow-up required</label>
      <label className="text-sm font-semibold">Follow-up notes<textarea name="follow_up_notes" rows={2} className="input-k mt-2" /></label>
      <button disabled={submitting} className="btn-orange mt-2 w-fit disabled:opacity-60"><AlertTriangle size={16} /> {submitting ? 'Submitting…' : 'Submit report'}</button>
    </form>}
  </VolunteerShell>
}
