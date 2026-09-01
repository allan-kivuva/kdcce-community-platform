import { NavLink, Link, useNavigate } from 'react-router-dom'
import { Bell, Calendar, Home, LayoutDashboard, MessageSquare, User } from 'lucide-react'
import ThemeToggle from '../../theme/ThemeToggle'
import NotificationBell from '../admin/NotificationBell'
import { getStoredUser, endSession } from '../../lib/api'
import { useCommunicationCounts } from '../../lib/useCommunicationCounts'

// A distinct shell from both Shell.jsx (admin) and VolunteerShell.jsx —
// simpler than either, and never links to any admin/volunteer-only
// navigation. Only what the Phase 8 brief lists for the family portal:
// Overview, Visits, Programs, Messages, Notifications, Profile.
const menu = [
  ['Overview', '/family', 'LayoutDashboard'],
  ['Visits', '/family/visits', 'Home'],
  ['Programs & Events', '/family/programs', 'Calendar'],
  ['Messages', '/family/messages', 'MessageSquare', 'unreadMessages'],
  ['Notifications', '/family/notifications', 'Bell'],
  ['Profile', '/family/profile', 'User'],
]
const icons = { LayoutDashboard, Home, Calendar, MessageSquare, Bell, User }

export default function FamilyShell({ children }) {
  const navigate = useNavigate()
  const user = getStoredUser()
  const { unreadMessages } = useCommunicationCounts(user?.role)
  const counts = { unreadMessages }
  async function signOut() { await endSession(); navigate('/admin/login') }

  return <div className="min-h-[80vh] bg-kCream">
    <div className="container-k grid gap-6 py-8 lg:grid-cols-[230px_1fr]">
      <aside className="rounded-2xl bg-kGreen p-4 text-white">
        <div className="mb-5 rounded-2xl bg-white px-3 py-3"><img src="/images/logo.png" alt="KDCCE" className="h-14 w-auto max-w-[185px] object-contain object-left" /></div>
        <div className="mb-4 flex items-center justify-between gap-2 px-3">
          <div>
            <div className="text-xs font-semibold uppercase tracking-widest text-kLime">Family portal</div>
            {user && <div className="mt-1 text-xs text-white/70">{user.name}</div>}
          </div>
          <div className="flex items-center gap-1"><NotificationBell variant="dark" /><ThemeToggle variant="dark" /></div>
        </div>
        <nav className="grid gap-1">
          {menu.map(([label, to, icon, badgeKey]) => {
            const Icon = icons[icon]
            const count = badgeKey ? counts[badgeKey] : 0
            return <NavLink end={to === '/family'} key={to} to={to} className={({ isActive }) => `flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-semibold ${isActive ? 'bg-white text-kGreen' : 'text-white/80 hover:bg-white/10 hover:text-white'}`}>
              <Icon size={17} />{label}
              {count > 0 && <span className="ml-auto grid h-5 min-w-[20px] place-items-center rounded-full bg-kOrange px-1 text-[10px] font-bold text-white">{count > 9 ? '9+' : count}</span>}
            </NavLink>
          })}
        </nav>
        <Link to="/" className="mt-6 flex items-center gap-3 rounded-xl px-3 py-3 text-sm text-white/80 hover:bg-white/10">Back to website</Link>
        <button onClick={signOut} className="mt-1 flex w-full items-center gap-3 rounded-xl px-3 py-3 text-sm text-white/80 hover:bg-white/10">Sign out</button>
      </aside>
      <section>{children}</section>
    </div>
  </div>
}
