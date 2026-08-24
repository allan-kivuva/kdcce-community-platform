import { NavLink, Link, useNavigate } from 'react-router-dom'
import { BookOpen, ClipboardCheck, FileImage, Heart, HeartPulse, HeartHandshake, Inbox, LayoutDashboard, LogOut, Package, Pill, User, UserRound, Users } from 'lucide-react'
import ThemeToggle from '../../theme/ThemeToggle'
import { getStoredUser, clearSession } from '../../lib/api'

// Single source of truth for the admin nav — every module page lives at
// its own route/file, but they all render inside this same Shell, so a
// new module only needs one entry added here to appear for everyone.
// Staff/admin see the full operational menu; a volunteer account sees
// only their own profile — the backend enforces this regardless (every
// staff-only route 403s a volunteer token), this just keeps a volunteer
// from staring at a nav full of links that don't work for them.
const staffMenu = [
  ['Overview', '/admin', 'LayoutDashboard'],
  ['Elderly Members', '/admin/elderly', 'UserRound'],
  ['Attendance', '/admin/attendance', 'ClipboardCheck'],
  ['Health & Wellness', '/admin/health', 'HeartPulse'],
  ['Medication', '/admin/medication', 'Pill'],
  ['Volunteers', '/admin/volunteers', 'HeartHandshake'],
  ['Donations', '/admin/donations', 'Heart'],
  ['Blog Posts', '/admin/blog', 'BookOpen'],
  ['Gallery', '/admin/gallery', 'FileImage'],
  ['Team', '/admin/team', 'Users'],
  ['Craft Shop', '/admin/crafts', 'Package'],
  ['Inbox', '/admin/inbox', 'Inbox'],
]
const volunteerMenu = [
  ['My Profile', '/admin/profile', 'User'],
]
const icons = { LayoutDashboard, Heart, HeartPulse, HeartHandshake, Pill, BookOpen, FileImage, Users, Package, Inbox, UserRound, ClipboardCheck, User }

export default function Shell({ children }) {
  const navigate = useNavigate()
  const user = getStoredUser()
  const menu = user?.role === 'volunteer' ? volunteerMenu : staffMenu
  function signOut() { clearSession(); navigate('/admin/login') }
  return <div className="min-h-[80vh] bg-kCream"><div className="container-k grid gap-6 py-8 lg:grid-cols-[230px_1fr]"><aside className="rounded-2xl bg-[#071724] p-4 text-white"><div className="mb-5 rounded-2xl bg-white px-3 py-3"><img src="/images/logo.png" alt="KDCCE" className="h-14 w-auto max-w-[185px] object-contain object-left" /></div><div className="mb-4 flex items-center justify-between gap-2 px-3"><div><div className="text-xs font-semibold uppercase tracking-widest text-kLime">Staff workspace</div><div className="mt-1 font-display text-xl font-bold">Admin portal</div>{user && <div className="mt-1 text-xs text-white/60">{user.name} &middot; {user.role}</div>}</div><ThemeToggle variant="dark" /></div><nav className="grid gap-1">{menu.map(([label, to, icon]) => { const Icon = icons[icon]; return <NavLink end={to === '/admin'} key={to} to={to} className={({ isActive }) => `flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-semibold ${isActive ? 'bg-white text-kGreen' : 'text-white/70 hover:bg-white/10 hover:text-white'}`}><Icon size={17} />{label}</NavLink> })}</nav><Link to="/" className="mt-6 flex items-center gap-3 rounded-xl px-3 py-3 text-sm text-white/70 hover:bg-white/10"><LogOut size={17} /> Back to website</Link><button onClick={signOut} className="mt-1 flex w-full items-center gap-3 rounded-xl px-3 py-3 text-sm text-white/70 hover:bg-white/10"><LogOut size={17} /> Sign out</button></aside><section>{children}</section></div></div>
}
