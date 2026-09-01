import { useCallback, useEffect, useRef, useState } from 'react'
import QRCode from 'qrcode'
import { AlertTriangle, CheckCircle2, KeyRound, ShieldCheck, ShieldOff, Smartphone } from 'lucide-react'
import Shell from '../../components/admin/Shell'
import { LoadingState, ErrorState, errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch, getStoredUser, getToken, setSession } from '../../lib/api'

function StatCard({ label, value, tone = 'default' }) {
  const tones = { default: 'text-kGreen', warning: 'text-amber-600', danger: 'text-red-500' }
  return <div className="card-k p-5">
    <div className="text-xs font-bold uppercase tracking-wide text-kMuted">{label}</div>
    <div className={`mt-2 font-display text-2xl font-bold ${tones[tone]}`}>{value}</div>
  </div>
}

function OverviewPanel() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try { setData(await apiFetch('/api/system/security-overview')) }
    catch (err) { setError(errorMessage(err)) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  if (loading) return <LoadingState label="security overview" rows={2} />
  if (error) return <ErrorState message={error} onRetry={load} />

  return <div className="grid gap-6">
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <StatCard label="API / DB" value={data.db_connected ? 'Healthy' : 'DB unreachable'} tone={data.db_connected ? 'default' : 'danger'} />
      <StatCard label="Active sessions" value={data.active_session_count} />
      <StatCard label="Disabled accounts" value={data.disabled_account_count} tone={data.disabled_account_count > 0 ? 'warning' : 'default'} />
      <StatCard label="Admin 2FA coverage" value={`${data.admin_2fa_coverage.enabled}/${data.admin_2fa_coverage.total}`} tone={data.admin_2fa_coverage.enabled < data.admin_2fa_coverage.total ? 'warning' : 'default'} />
    </div>

    <div className="grid gap-6 lg:grid-cols-2">
      <div className="card-k p-5">
        <h2 className="font-display text-lg font-bold text-kGreen">Recent failed logins (24h)</h2>
        <div className="mt-3 grid gap-2">
          {data.recent_failed_logins.length === 0 && <p className="text-sm text-kMuted">None recorded — nothing to review.</p>}
          {data.recent_failed_logins.map(l => <div key={l.id} className="flex items-center justify-between rounded-xl bg-kCream px-3 py-2 text-sm">
            <span className="font-semibold text-kInk">{l.attempted_email || l.user_name || 'Unknown'}</span>
            <span className="text-xs text-kMuted">{l.failure_reason} &middot; {new Date(l.created_at).toLocaleTimeString()}</span>
          </div>)}
        </div>
      </div>
      <div className="card-k p-5">
        <h2 className="font-display text-lg font-bold text-kGreen">Recent critical events</h2>
        <div className="mt-3 grid gap-2">
          {data.recent_critical_events.length === 0 && <p className="text-sm text-kMuted">No critical account/access changes recently.</p>}
          {data.recent_critical_events.map(e => <div key={e.id} className="flex items-center justify-between rounded-xl bg-kCream px-3 py-2 text-sm">
            <span className="font-semibold text-kInk">{e.actor} &middot; {e.action}</span>
            <span className="text-xs text-kMuted">{e.resource_type} #{e.resource_id}</span>
          </div>)}
        </div>
      </div>
    </div>
    {data.commit && <p className="text-xs text-kMuted">Build: {data.commit}</p>}
  </div>
}

function TwoFactorPanel({ showToast }) {
  const [user, setUser] = useState(getStoredUser())
  const [stage, setStage] = useState('idle') // idle | setup | recovery
  const [secret, setSecret] = useState(null)
  const [otpauthUri, setOtpauthUri] = useState(null)
  const [code, setCode] = useState('')
  const [recoveryCodes, setRecoveryCodes] = useState(null)
  const [busy, setBusy] = useState(false)
  const canvasRef = useRef(null)

  useEffect(() => {
    if (stage === 'setup' && otpauthUri && canvasRef.current) {
      QRCode.toCanvas(canvasRef.current, otpauthUri, { width: 200, margin: 1, color: { dark: '#071724', light: '#ffffff' } }).catch(() => {})
    }
  }, [stage, otpauthUri])

  async function startSetup() {
    setBusy(true)
    try {
      const res = await apiFetch('/api/auth/2fa/setup', { method: 'POST' })
      setSecret(res.secret)
      setOtpauthUri(res.otpauth_uri)
      setStage('setup')
    } catch (err) { showToast(errorMessage(err)) }
    finally { setBusy(false) }
  }

  async function confirmSetup(e) {
    e.preventDefault()
    setBusy(true)
    try {
      const res = await apiFetch('/api/auth/2fa/verify-setup', { method: 'POST', body: { code } })
      setRecoveryCodes(res.recovery_codes)
      setStage('recovery')
      const updatedUser = { ...user, two_factor_enabled: true }
      setSession(getToken(), updatedUser)
      setUser(updatedUser)
    } catch (err) { showToast(errorMessage(err)) }
    finally { setBusy(false) }
  }

  function finishRecovery() {
    setStage('idle')
    setCode('')
    setSecret(null)
    setOtpauthUri(null)
    setRecoveryCodes(null)
    showToast('Two-factor authentication enabled')
  }

  async function disable() {
    const password = window.prompt('Enter your current password to disable two-factor authentication:')
    if (!password) return
    setBusy(true)
    try {
      await apiFetch('/api/auth/2fa/disable', { method: 'POST', body: { password } })
      const updatedUser = { ...user, two_factor_enabled: false }
      setSession(getToken(), updatedUser)
      setUser(updatedUser)
      showToast('Two-factor authentication disabled')
    } catch (err) { showToast(errorMessage(err)) }
    finally { setBusy(false) }
  }

  return <div className="card-k p-6">
    <div className="flex items-center gap-3">
      <div className={`grid h-11 w-11 place-items-center rounded-full ${user?.two_factor_enabled ? 'bg-emerald-500/10 text-emerald-500' : 'bg-kTint text-kOrange'}`}>
        {user?.two_factor_enabled ? <ShieldCheck size={20} /> : <Smartphone size={20} />}
      </div>
      <div>
        <h2 className="font-display text-lg font-bold text-kGreen">Two-factor authentication</h2>
        <p className="text-sm text-kMuted">{user?.two_factor_enabled ? 'Enabled — an authenticator code is required at every login.' : 'Not enabled on your account yet.'}</p>
      </div>
    </div>

    {stage === 'idle' && (
      user?.two_factor_enabled
        ? <button disabled={busy} onClick={disable} className="mt-5 flex items-center gap-2 rounded-xl border border-red-200 px-4 py-2.5 text-sm font-bold text-red-500 hover:bg-red-50 disabled:opacity-60"><ShieldOff size={16} /> Disable 2FA</button>
        : <button disabled={busy} onClick={startSetup} className="btn-orange mt-5"><KeyRound size={16} /> Set up 2FA</button>
    )}

    {stage === 'setup' && (
      <div className="mt-5 grid gap-4 sm:grid-cols-[200px_1fr]">
        <canvas ref={canvasRef} className="rounded-xl border border-kBorderSoft" />
        <div>
          <p className="text-sm text-kInk">Scan this QR code with an authenticator app (Google Authenticator, Authy, 1Password, ...), or enter the code manually:</p>
          <code className="mt-2 block break-all rounded-lg bg-kCream px-3 py-2 text-xs">{secret}</code>
          <form onSubmit={confirmSetup} className="mt-4 flex items-end gap-3">
            <label className="text-sm font-semibold">Enter the 6-digit code<input value={code} onChange={e => setCode(e.target.value)} className="input-k mt-2 w-32" maxLength={6} required /></label>
            <button disabled={busy} className="btn-orange disabled:opacity-60">Confirm</button>
          </form>
        </div>
      </div>
    )}

    {stage === 'recovery' && recoveryCodes && (
      <div className="mt-5">
        <div className="flex items-center gap-2 text-sm font-bold text-amber-600"><AlertTriangle size={16} /> Save these recovery codes now — they will not be shown again.</div>
        <div className="mt-3 grid grid-cols-2 gap-2 rounded-xl bg-kCream p-4 font-mono text-sm">
          {recoveryCodes.map(c => <div key={c}>{c}</div>)}
        </div>
        <button onClick={finishRecovery} className="btn-orange mt-4"><CheckCircle2 size={16} /> I've saved my recovery codes</button>
      </div>
    )}
  </div>
}

export default function SecurityDashboard({ showToast }) {
  const user = getStoredUser()
  return <Shell>
    <div><div className="eyebrow">Administration</div><h1 className="font-display text-3xl font-bold text-kGreen">Security</h1></div>
    <p className="mt-2 max-w-2xl text-sm text-kMuted">Platform-wide security posture, plus your own account's two-factor authentication.</p>

    <div className="mt-6"><OverviewPanel /></div>
    <div className="mt-6">
      {user?.role === 'admin'
        ? <TwoFactorPanel showToast={showToast} />
        : <div className="card-k p-6 text-sm text-kMuted">Two-factor authentication is currently available to admin accounts only.</div>}
    </div>
  </Shell>
}
