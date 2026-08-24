import { useState, useEffect, useCallback } from 'react'
import { Routes, Route, useNavigate } from 'react-router-dom'
import { Clock, XCircle } from 'lucide-react'
import ThemeToggle from '../theme/ThemeToggle'
import { LoadingState, ErrorState, errorMessage, useToast } from '../components/admin/adminHelpers'
import { apiFetch, getStoredUser, endSession, clearSession, ApiError } from '../lib/api'
import VolunteerDashboard from './volunteer/VolunteerDashboard'
import MyVolunteerProfile from './volunteer/MyVolunteerProfile'
import MyAssignments from './volunteer/MyAssignments'
import MyAssistanceRequests from './volunteer/MyAssistanceRequests'
import MyElderlyMembers from './volunteer/MyElderlyMembers'
import MyActivity from './volunteer/MyActivity'
import MyPerformance from './volunteer/MyPerformance'
import VolunteerMessages from './volunteer/VolunteerMessages'
import ReportConcern from './volunteer/ReportConcern'
import VolunteerNotifications from './volunteer/VolunteerNotifications'
import Toast from '../components/admin/Toast'
import { VolunteerDataProvider } from '../lib/VolunteerDataContext'

function StatusScreen({ icon, title, children, onSignOut }) {
  return <div className="grid min-h-[80vh] place-items-center bg-kCream px-5"><div className="w-full max-w-md text-center">
    <div className="mb-4 flex justify-end"><ThemeToggle /></div>
    <div className="card-k p-9">
      <div className="mx-auto grid h-16 w-16 place-items-center rounded-full bg-kTint text-kOrange">{icon}</div>
      <h1 className="mt-5 font-display text-2xl font-bold text-kGreen">{title}</h1>
      <div className="mt-3 text-sm leading-6 text-kMuted">{children}</div>
      <button onClick={onSignOut} className="mt-7 text-sm font-semibold text-kOrange">Sign out</button>
    </div>
  </div></div>
}

export default function VolunteerPortal() {
  const navigate = useNavigate()
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [toast, showToast] = useToast()

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await apiFetch('/api/volunteers/me')
      setProfile(res.volunteer)
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) { clearSession(); navigate('/admin/login'); return }
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [navigate])

  useEffect(() => {
    // This gate is enforced server-side too (list/get/update on
    // home-visits and assistance-requests 403 a non-Verified volunteer,
    // and GET /api/volunteers/me itself requires auth) — this is only
    // the frontend's reflection of that, deciding which screen to render.
    const user = getStoredUser()
    if (!user) { navigate('/admin/login'); return }
    if (user.role !== 'volunteer') { navigate('/admin'); return }
    load()
  }, [load, navigate])

  async function signOut() { await endSession(); navigate('/admin/login') }

  if (loading) return <div className="min-h-[80vh] bg-kCream py-24"><LoadingState label="your account" /></div>
  if (error) return <div className="min-h-[80vh] bg-kCream py-24"><ErrorState message={error} onRetry={load} /></div>

  if (profile.status === 'Pending') {
    return <StatusScreen icon={<Clock />} title="Application under review" onSignOut={signOut}>
      Thanks for applying, {profile.name.split(' ')[0]}. KDCCE staff are reviewing your application and will get back to you soon. You can update your details any time — sign back in to check your status.
    </StatusScreen>
  }
  if (profile.status === 'Rejected') {
    return <StatusScreen icon={<XCircle />} title="Application not approved" onSignOut={signOut}>
      Your volunteer application was not approved.{profile.rejection_reason ? ` ${profile.rejection_reason}` : ''} Contact KDCCE staff with any questions.
    </StatusScreen>
  }

  return <VolunteerDataProvider>
    <Routes>
      <Route index element={<VolunteerDashboard profile={profile} />} />
      <Route path="profile" element={<MyVolunteerProfile showToast={showToast} />} />
      <Route path="home-visits" element={<MyAssignments showToast={showToast} />} />
      <Route path="assistance" element={<MyAssistanceRequests showToast={showToast} />} />
      <Route path="elderly-members" element={<MyElderlyMembers />} />
      <Route path="activity" element={<MyActivity />} />
      <Route path="performance" element={<MyPerformance />} />
      <Route path="messages" element={<VolunteerMessages />} />
      <Route path="report-concern" element={<ReportConcern showToast={showToast} />} />
      <Route path="notifications" element={<VolunteerNotifications />} />
    </Routes>
    <Toast message={toast} />
  </VolunteerDataProvider>
}
