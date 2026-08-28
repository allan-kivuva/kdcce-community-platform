import { NavLink, Link, useNavigate } from 'react-router-dom'
import { LayoutDashboard, User, Home, HandHeart, Bell, Users, History, TrendingUp, MessageSquare, AlertTriangle } from 'lucide-react'
import ThemeToggle from '../../theme/ThemeToggle'
import NotificationBell from '../admin/NotificationBell'
import { getStoredUser, endSession } from '../../lib/api'

// A separate shell from components/admin/Shell.jsx on purpose: the
// volunteer portal is its own workspace (its own nav, its own route
// space at /volunteer/*), not a role-switched view inside the staff
// admin dashboard — see VolunteerPortal.jsx for the approval gate that
// decides whether a volunteer ever reaches this shell at all. Only
// volunteer-relevant nav here — never the admin/staff management menu.
const menu = [
  ['Dashboard', '/volunteer', 'LayoutDashboard'],
  ['My Home Visits', '/volunteer/home-visits', 'Home'],
  ['Assistance Requests', '/volunteer/assistance', 'HandHeart'],
  ['My Elderly Members', '/volunteer/elderly-members', 'Users'],
  ['My Activity', '/volunteer/activity', 'History'],
  ['My Performance', '/volunteer/performance', 'TrendingUp'],
  ['Messages', '/volunteer/messages', 'MessageSquare'],
  ['Report a Concern', '/volunteer/report-concern', 'AlertTriangle'],
  ['Notifications', '/volunteer/notifications', 'Bell'],
  ['My Profile', '/volunteer/profile', 'User'],
]
const icons = { LayoutDashboard, User, Home, HandHeart, Bell, Users, History, TrendingUp, MessageSquare, AlertTriangle }

export default function VolunteerShell({ children }) {
  const navigate = useNavigate()
  const user = getStoredUser()
  async function signOut() { await endSession(); navigate('/admin/login') }
  return <div className="min-h-[80vh] bg-kCream"><div className="container-k grid gap-6 py-8 lg:grid-cols-[230px_1fr]"><aside className="rounded-2xl bg-[#071724] p-4 text-white"><div className="mb-5 rounded-2xl bg-white px-3 py-3"><img src="/images/logo.png" alt="KDCCE" className="h-14 w-auto max-w-[185px] object-contain object-left" /></div><div className="mb-4 flex items-center justify-between gap-2 px-3"><div><div className="text-xs font-semibold uppercase tracking-widest text-kLime">Volunteer portal</div>{user && <div className="mt-1 text-xs text-white/60">{user.name}</div>}</div><div className="flex items-center gap-1"><NotificationBell variant="dark" /><ThemeToggle variant="dark" /></div></div><nav className="grid gap-1">{menu.map(([label, to, icon]) => { const Icon = icons[icon]; return <NavLink end={to === '/volunteer'} key={to} to={to} className={({ isActive }) => `flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-semibold ${isActive ? 'bg-white text-kGreen' : 'text-white/70 hover:bg-white/10 hover:text-white'}`}><Icon size={17} />{label}</NavLink> })}</nav><Link to="/" className="mt-6 flex items-center gap-3 rounded-xl px-3 py-3 text-sm text-white/70 hover:bg-white/10">Back to website</Link><button onClick={signOut} className="mt-1 flex w-full items-center gap-3 rounded-xl px-3 py-3 text-sm text-white/70 hover:bg-white/10">Sign out</button></aside><section>{children}</section></div></div>
}
