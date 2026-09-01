import { useState, useEffect, useRef, useCallback } from 'react'
import QRCode from 'qrcode'
import { BadgeCheck, Clock, RefreshCw, ShieldCheck, XCircle } from 'lucide-react'
import VolunteerShell from '../../components/volunteer/VolunteerShell'
import { LoadingState, ErrorState, errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch } from '../../lib/api'

const STATUS_META = {
  Verified: { icon: ShieldCheck, style: 'bg-emerald-500 text-white', label: 'Verified' },
  Pending: { icon: Clock, style: 'bg-amber-500 text-white', label: 'Pending' },
  Rejected: { icon: XCircle, style: 'bg-red-500 text-white', label: 'Not Approved' },
}

function initials(name) { return (name || '?').split(' ').map(p => p[0]).slice(0, 2).join('').toUpperCase() }

export default function DigitalId() {
  const [id, setId] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [qrLoading, setQrLoading] = useState(false)
  const canvasRef = useRef(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try { setId((await apiFetch('/api/volunteers/me/digital-id')).digital_id) }
    catch (err) { setError(errorMessage(err)) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const generateQr = useCallback(async () => {
    setQrLoading(true)
    try {
      const { token } = await apiFetch('/api/volunteers/me/digital-id/qr-token')
      if (canvasRef.current) {
        await QRCode.toCanvas(canvasRef.current, token, { width: 200, margin: 1, color: { dark: '#071724', light: '#ffffff' } })
      }
    } catch { /* QR is a bonus on top of the ID card itself — a failed generation just leaves the placeholder */ }
    finally { setQrLoading(false) }
  }, [])

  useEffect(() => { if (id) generateQr() }, [id, generateQr])

  if (loading) return <VolunteerShell><LoadingState label="digital ID" /></VolunteerShell>
  if (error) return <VolunteerShell><ErrorState message={error} onRetry={load} /></VolunteerShell>

  const meta = STATUS_META[id.status] || STATUS_META.Pending

  return <VolunteerShell>
    <div><div className="eyebrow">My credentials</div><h1 className="font-display text-3xl font-bold text-kGreen">Digital Volunteer ID</h1></div>

    <div className="mx-auto mt-7 max-w-md">
      <div className="overflow-hidden rounded-3xl border border-kBorderSoft bg-gradient-to-br from-[#071724] to-[#0c2a3d] text-white shadow-soft">
        <div className="flex items-center gap-3 border-b border-white/10 px-6 py-4">
          <img src="/images/logo.png" alt="KDCCE" className="h-9 w-9 rounded-lg bg-white object-contain p-1" />
          <div className="flex-1">
            <div className="text-sm font-bold">KDCCE Volunteer</div>
            <div className="text-[11px] text-white/60">Empowering care. Enriching lives.</div>
          </div>
          <BadgeCheck size={20} className="text-blue-300" />
        </div>

        <div className="p-6">
          <div className="flex items-center gap-4">
            <div className="grid h-16 w-16 shrink-0 place-items-center rounded-full bg-white/10 text-xl font-bold">{initials(id.name)}</div>
            <div className="min-w-0">
              <div className="truncate font-display text-xl font-bold">{id.name}</div>
              <div className="text-xs text-white/60">{id.volunteer_code}</div>
              <span className={`mt-1.5 inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-bold ${meta.style}`}><meta.icon size={12} /> {meta.label}</span>
            </div>
          </div>

          {(id.skills || id.areas_of_interest) && <div className="mt-5 grid gap-2 border-t border-white/10 pt-4 text-xs">
            {id.skills && <div><span className="text-white/50">Skills: </span><span className="text-white/90">{id.skills}</span></div>}
            {id.areas_of_interest && <div><span className="text-white/50">Focus areas: </span><span className="text-white/90">{id.areas_of_interest}</span></div>}
          </div>}

          <div className="mt-5 flex items-center justify-between gap-4 border-t border-white/10 pt-5">
            <div className="text-[11px] text-white/50">Volunteer since<br /><span className="text-sm font-semibold text-white">{new Date(id.member_since).toLocaleDateString([], { dateStyle: 'medium' })}</span></div>
            <div className="grid place-items-center rounded-xl bg-white p-2">
              <canvas ref={canvasRef} className="h-[100px] w-[100px]" />
            </div>
          </div>
        </div>
      </div>

      <button onClick={generateQr} disabled={qrLoading} className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl border border-kBorder px-4 py-2.5 text-sm font-semibold text-kMuted hover:bg-kCream disabled:opacity-60">
        <RefreshCw size={14} className={qrLoading ? 'animate-spin' : ''} /> Refresh code
      </button>
      <p className="mt-2 text-center text-xs text-kMuted">This code expires after 5 minutes. Staff can scan or enter it to confirm your identity — it never reveals your email or phone number.</p>
    </div>
  </VolunteerShell>
}
