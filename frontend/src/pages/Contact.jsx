import { Mail, MapPin, Phone, Send, AlertCircle } from 'lucide-react'
import { useState } from 'react'
import PageHero from '../components/PageHero'
import { apiFetch, ApiError } from '../lib/api'

export default function Contact(){
  const [sent,setSent]=useState(false)
  const [submitting,setSubmitting]=useState(false)
  const [error,setError]=useState('')

  async function handleSubmit(e){
    e.preventDefault()
    setError('')
    setSubmitting(true)
    const f = new FormData(e.target)
    try {
      await apiFetch('/api/inbox', {
        method: 'POST',
        auth: false,
        body: {
          name: f.get('name'),
          email: f.get('email'),
          subject: f.get('subject'),
          message: f.get('message'),
        },
      })
      setSent(true)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return <><PageHero title="Let's stay connected" eyebrow="Contact" text="Questions, partnerships, volunteering or a message for the team? Send it through the form." image="/images/contact.jpg"/><section className="container-k grid gap-8 py-20 md:grid-cols-[.8fr_1.2fr]"><div className="rounded-2xl bg-kGreen p-8 text-white"><h2 className="font-display text-3xl font-bold">Contact details</h2><p className="mt-3 leading-7 text-white/70">Messages sent through this form go straight to our team's inbox.</p><div className="mt-8 grid gap-5"><div className="flex gap-3"><Phone className="text-orange-300"/> <div><b className="block">Phone</b><span className="text-sm text-white/65">+254 724 380 025</span></div></div><div className="flex gap-3"><Mail className="text-orange-300"/> <div><b className="block">Email</b><span className="text-sm text-white/65">info@kdcce.org</span></div></div><div className="flex gap-3"><MapPin className="text-orange-300"/> <div><b className="block">Location</b><span className="text-sm text-white/65">Kibera, Nairobi, Kenya</span></div></div></div><div className="mt-10 rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-white/60">Map integration can be added here after the backend and deployment setup.</div></div><div className="card-k p-7 md:p-9">{sent?<div className="py-10 text-center"><div className="mx-auto grid h-16 w-16 place-items-center rounded-full bg-kTint text-kOrange"><Send/></div><h2 className="mt-5 font-display text-3xl font-bold text-kGreen">Message sent</h2><p className="mt-3 text-kMuted">Thank you — our team will get back to you soon.</p></div>:<form onSubmit={handleSubmit}><div className="eyebrow">Send a message</div><h2 className="mt-2 font-display text-3xl font-bold text-kGreen">How can we help?</h2>{error && <div className="mt-4 flex items-center gap-2 rounded-xl bg-red-50 px-4 py-3 text-sm font-semibold text-red-700"><AlertCircle size={16}/> {error}</div>}<div className="mt-7 grid gap-4 md:grid-cols-2"><label className="text-sm font-semibold">Name<input name="name" className="input-k mt-2" required/></label><label className="text-sm font-semibold">Email<input name="email" className="input-k mt-2" type="email" required/></label><label className="text-sm font-semibold md:col-span-2">Subject<input name="subject" className="input-k mt-2" required/></label><label className="text-sm font-semibold md:col-span-2">Message<textarea name="message" className="input-k mt-2 min-h-40" required/></label></div><button className="btn-orange mt-6" disabled={submitting}><Send size={16}/> {submitting ? 'Sending…' : 'Send Message'}</button></form>}</div></section></>
}
