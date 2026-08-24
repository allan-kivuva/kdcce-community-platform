import { useState, useEffect, useCallback } from 'react'
import VolunteerShell from '../../components/volunteer/VolunteerShell'
import { LoadingState, ErrorState, errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch } from '../../lib/api'

const STATUS_COPY = {
  Pending: 'Your profile is awaiting review by KDCCE staff.',
  Verified: "You're verified — staff can now assign you to home visits and activities.",
  Rejected: 'Your volunteer application was not approved. Contact KDCCE staff with any questions.',
}
const STATUS_STYLES = {
  Pending: 'bg-kTint text-kOrange',
  Verified: 'bg-kGreen/10 text-kGreen',
  Rejected: 'bg-red-100 text-red-700',
}

export default function MyVolunteerProfile({ showToast }) {
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try { setProfile((await apiFetch('/api/volunteers/me')).volunteer) }
    catch (err) { setError(errorMessage(err)) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  async function save(e) {
    e.preventDefault()
    const f = new FormData(e.target)
    const data = {
      phone: f.get('phone') || null,
      skills: f.get('skills') || null,
      availability: f.get('availability') || null,
      bio: f.get('bio') || null,
    }
    setSaving(true)
    try {
      const res = await apiFetch('/api/volunteers/me', { method: 'PATCH', body: data })
      setProfile(res.volunteer)
      showToast('Profile updated')
    } catch (err) { showToast(errorMessage(err)) }
    finally { setSaving(false) }
  }

  return <VolunteerShell>
    <div><div className="eyebrow">My account</div><h1 className="font-display text-3xl font-bold text-kGreen">My volunteer profile</h1></div>

    {loading ? <LoadingState label="profile" /> : error ? <ErrorState message={error} onRetry={load} /> : <>
      <div className="card-k mt-7 p-6">
        <span className={`rounded-full px-3 py-1 text-xs font-bold ${STATUS_STYLES[profile.status]}`}>{profile.status}</span>
        <p className="mt-3 text-sm text-kMuted">{STATUS_COPY[profile.status]}</p>
      </div>

      <form onSubmit={save} className="card-k mt-6 grid gap-4 p-6">
        <h2 className="font-display text-lg font-bold text-kGreen">Your details</h2>
        <label className="text-sm font-semibold">Phone<input name="phone" defaultValue={profile.phone || ''} className="input-k mt-2" /></label>
        <label className="text-sm font-semibold">Skills<textarea name="skills" defaultValue={profile.skills || ''} rows={2} className="input-k mt-2" placeholder="e.g. First aid, cooking, transport" /></label>
        <label className="text-sm font-semibold">Availability<textarea name="availability" defaultValue={profile.availability || ''} rows={2} className="input-k mt-2" placeholder="e.g. Weekday mornings" /></label>
        <label className="text-sm font-semibold">About you<textarea name="bio" defaultValue={profile.bio || ''} rows={3} className="input-k mt-2" /></label>
        <button disabled={saving} className="btn-orange mt-2 w-fit disabled:opacity-60">{saving ? 'Saving…' : 'Save changes'}</button>
      </form>
    </>}
  </VolunteerShell>
}
