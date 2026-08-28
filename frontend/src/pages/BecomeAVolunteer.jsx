import { useState } from 'react'
import { Link } from 'react-router-dom'
import { CheckCircle2, HeartHandshake, AlertCircle, Clock } from 'lucide-react'
import PageHero from '../components/PageHero'
import { apiFetch, setSession, ApiError } from '../lib/api'

const AREAS = ['Home visits', 'Feeding program', 'Health & wellness support', 'Activities & companionship', 'Fundraising & events', 'Admin & office support']

export default function BecomeAVolunteer() {
  const [submitted, setSubmitted] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    const f = new FormData(e.target)

    const password = f.get('password')
    if (password !== f.get('confirm_password')) {
      setError('Passwords do not match.')
      return
    }
    const areas = AREAS.filter(a => f.get(`area_${a}`)).join(', ')

    setSubmitting(true)
    try {
      // Registration and the application are two calls against existing
      // endpoints, not a new combined one: POST /api/auth/register creates
      // the account (always role=volunteer, always starts Pending), then
      // this PATCH fills in everything a plain register doesn't collect.
      const { access_token, refresh_token, user } = await apiFetch('/api/auth/register', {
        method: 'POST',
        auth: false,
        body: { name: f.get('name'), email: f.get('email'), password },
      })
      setSession(access_token, user, refresh_token)

      try {
        await apiFetch('/api/volunteers/me', {
          method: 'PATCH',
          body: {
            phone: f.get('phone') || null,
            skills: f.get('skills') || null,
            availability: f.get('availability') || null,
            areas_of_interest: areas || null,
            experience: f.get('experience') || null,
            motivation: f.get('motivation') || null,
            bio: f.get('bio') || null,
          },
        })
      } catch {
        // The account exists either way — an applicant who lands here can
        // still see/complete their application from the volunteer portal's
        // pending-review screen, so this isn't a dead end.
      }
      setSubmitted(true)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  if (submitted) {
    return <><PageHero title="Application submitted" eyebrow="Become a volunteer" text="Thank you for applying to volunteer with KDCCE." image="/images/healthcare.jpg" />
      <section className="container-k py-20"><div className="mx-auto max-w-xl card-k p-10 text-center">
        <div className="mx-auto grid h-16 w-16 place-items-center rounded-full bg-kTint text-kOrange"><Clock /></div>
        <h2 className="mt-5 font-display text-3xl font-bold text-kGreen">Your application is under review</h2>
        <p className="mt-3 leading-7 text-kMuted">KDCCE staff will review your application and get back to you. You can sign in any time to check your status.</p>
        <Link to="/admin/login" className="btn-orange mt-7 inline-flex">Sign in to check status</Link>
      </div></section>
    </>
  }

  return <>
    <PageHero title="Become a Volunteer" eyebrow="Get involved" text="Tell us about yourself and how you'd like to help. Our team reviews every application before granting portal access." image="/images/healthcare.jpg" />
    <section className="container-k grid gap-10 py-20 md:grid-cols-[.7fr_1.3fr]">
      <div className="rounded-2xl bg-kGreen p-8 text-white">
        <div className="grid h-14 w-14 place-items-center rounded-2xl bg-kOrange"><HeartHandshake /></div>
        <h2 className="mt-6 font-display text-2xl font-bold">What happens next?</h2>
        <div className="mt-6 grid gap-4 text-sm leading-6 text-white/75">
          <p>1. Submit your application below.</p>
          <p>2. Our staff reviews it — usually within a few days.</p>
          <p>3. Once approved, you'll get full access to the volunteer portal: your assignments, home visits and assistance requests.</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="card-k p-7 md:p-9">
        {error && <div className="mb-6 flex items-center gap-2 rounded-xl bg-red-50 px-4 py-3 text-sm font-semibold text-red-700"><AlertCircle size={16} /> {error}</div>}

        <div className="eyebrow">Personal information</div>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <label className="text-sm font-semibold">Full name<input name="name" className="input-k mt-2" required /></label>
          <label className="text-sm font-semibold">Email<input name="email" type="email" className="input-k mt-2" required /></label>
          <label className="text-sm font-semibold">Phone number<input name="phone" className="input-k mt-2" placeholder="07XXXXXXXX" required /></label>
          <div />
          <label className="text-sm font-semibold">Password<input name="password" type="password" className="input-k mt-2" minLength={8} required /></label>
          <label className="text-sm font-semibold">Confirm password<input name="confirm_password" type="password" className="input-k mt-2" minLength={8} required /></label>
        </div>

        <div className="eyebrow mt-8">Volunteer information</div>
        <div className="mt-4 grid gap-4">
          <label className="text-sm font-semibold">Skills<textarea name="skills" rows={2} className="input-k mt-2" placeholder="e.g. First aid, cooking, transport, counselling" required /></label>
          <label className="text-sm font-semibold">Availability<textarea name="availability" rows={2} className="input-k mt-2" placeholder="e.g. Weekday mornings, weekends" required /></label>
          <div>
            <span className="text-sm font-semibold">Areas of interest</span>
            <div className="mt-2 grid gap-2 sm:grid-cols-2">
              {AREAS.map(a => <label key={a} className="flex items-center gap-2 text-sm text-kInk"><input type="checkbox" name={`area_${a}`} className="h-4 w-4" /> {a}</label>)}
            </div>
          </div>
          <label className="text-sm font-semibold">Relevant experience<textarea name="experience" rows={2} className="input-k mt-2" placeholder="Any past volunteering or related experience" /></label>
          <label className="text-sm font-semibold">Why do you want to volunteer with KDCCE?<textarea name="motivation" rows={3} className="input-k mt-2" required /></label>
          <label className="text-sm font-semibold">About you<textarea name="bio" rows={3} className="input-k mt-2" placeholder="A short bio our staff can get to know you by" /></label>
        </div>

        <button disabled={submitting} className="btn-orange mt-7 w-full disabled:opacity-60"><CheckCircle2 size={16} /> {submitting ? 'Submitting…' : 'Submit application'}</button>
      </form>
    </section>
  </>
}
