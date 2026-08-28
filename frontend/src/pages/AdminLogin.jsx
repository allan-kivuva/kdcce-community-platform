import { useState } from 'react'
import { LockKeyhole, ShieldCheck, AlertCircle } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import ThemeToggle from '../theme/ThemeToggle'
import { apiFetch, setSession, ApiError } from '../lib/api'

export default function AdminLogin(){
  const navigate = useNavigate()
  const [signingIn, setSigningIn] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e){
    e.preventDefault()
    setError('')
    setSigningIn(true)
    const f = new FormData(e.target)
    try {
      const { access_token, refresh_token, user } = await apiFetch('/api/auth/login', {
        method: 'POST',
        auth: false,
        body: { email: f.get('email'), password: f.get('password') }
      })
      setSession(access_token, user, refresh_token)
      navigate(user.role === 'volunteer' ? '/volunteer' : '/admin')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Sign in failed. Please try again.')
      setSigningIn(false)
    }
  }

  return <div className="relative min-h-[75vh] overflow-hidden py-20">
    <div className="absolute inset-0 bg-cover bg-center" style={{ backgroundImage: "url('/images/admin-login-bg.jpg')" }} />
    <div className="absolute inset-0 bg-gradient-to-b from-kInk/80 via-kInk/70 to-kInk/85" />
    <div className="relative mx-auto max-w-md px-5"><div className="mb-4 flex justify-end"><ThemeToggle /></div><div className="mb-6 text-center"><img src="/images/logo.png" alt="KDCCE" className="mx-auto h-20 w-auto object-contain"/><div className="mx-auto mt-4 grid h-12 w-12 place-items-center rounded-2xl bg-kGreen text-white"><ShieldCheck/></div><h1 className="mt-5 font-display text-3xl font-bold text-white">Staff portal</h1><p className="mt-2 text-sm text-white/80">Sign in with your staff, admin, or volunteer account.</p></div><form className="card-k p-7" onSubmit={handleSubmit}>{error && <div className="mb-5 flex items-start gap-2 rounded-xl bg-kTint p-3 text-sm text-kOrange"><AlertCircle size={16} className="mt-0.5 shrink-0"/> {error}</div>}<label className="text-sm font-semibold">Email<input name="email" className="input-k mt-2" type="email" placeholder="staff@kdcce.org" required/></label><label className="mt-4 block text-sm font-semibold">Password<input name="password" className="input-k mt-2" type="password" placeholder="••••••••" required/></label><button disabled={signingIn} className="btn-orange mt-6 w-full disabled:opacity-60"><LockKeyhole size={16}/> {signingIn ? 'Signing in…' : 'Sign in'}</button></form></div></div>
}
