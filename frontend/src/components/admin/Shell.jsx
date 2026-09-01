import { useEffect, useRef, useState } from 'react'
import { NavLink, Link, useNavigate } from 'react-router-dom'
import {
  Activity, BadgeCheck, Bot, BookOpen, Boxes, CalendarDays, ChevronDown, ClipboardCheck, FileBarChart, FileCheck, FileImage, Gauge,
  GraduationCap, HandHeart, Heart, HeartPulse, HeartHandshake, History, Home, Inbox, Laptop, Layers, LayoutDashboard,
  Link2, ListChecks, LogOut, Map, Megaphone, Menu, MessageSquare, Package, Pill, Receipt, Repeat, Settings as SettingsIcon,
  ShieldAlert, ShieldCheck, Sparkles, Target, TrendingUp, Upload, UserRound, Users, Utensils, Wallet, X,
} from 'lucide-react'
import ThemeToggle from '../../theme/ThemeToggle'
import NotificationBell from './NotificationBell'
import GlobalSearch from './GlobalSearch'
import QuickActionMenu from './QuickActionMenu'
import { apiFetch, getStoredUser, endSession } from '../../lib/api'

// Single source of truth for the admin nav — every module page lives at
// its own route/file, but they all render inside this same Shell, so a
// new module only needs one entry added here to appear for everyone.
// Split into `primary` (shown directly in the top nav bar) and
// `secondary` (collapsed into the "More" dropdown / mobile drawer) —
// nothing here was removed from the old sidebar menu, it's the exact
// same route list, just organized for a horizontal bar instead of an
// unlimited-height vertical list.
// Staff/admin only: a volunteer account never reaches /admin/* at all —
// AdminLogin redirects a volunteer straight to /volunteer, which has its
// own separate shell (components/volunteer/VolunteerShell.jsx) and its
// own approval gate (pages/VolunteerPortal.jsx).
const primaryMenu = [
  ['Dashboard', '/admin', 'LayoutDashboard', true],
  ['Volunteers', '/admin/volunteers', 'HeartHandshake'],
  ['Elderly Members', '/admin/elderly', 'UserRound'],
  ['Requests', '/admin/assistance', 'HandHeart', false, 'requests'],
  ['Home Visits', '/admin/home-visits', 'Home'],
  ['Messages', '/admin/messages', 'MessageSquare', false, 'directMessages'],
  ['Contact Inbox', '/admin/inbox', 'Inbox', false, 'messages'],
  ['Programs', '/admin/programs', 'Layers'],
  ['Activities', '/admin/activities', 'Activity'],
  ['Finance', '/admin/finance', 'Wallet'],
  ['Reports', '/admin/reports', 'FileBarChart'],
  ['Security', '/admin/security', 'ShieldCheck'],
]
const secondaryMenu = [
  ['AI Assistant', '/admin/ai-assistant', 'Bot'],
  ['AI Insights', '/admin/ai-insights', 'TrendingUp'],
  ['Analytics', '/admin/analytics', 'Gauge'],
  ['Attendance', '/admin/attendance', 'ClipboardCheck'],
  ['Health & Wellness', '/admin/health', 'HeartPulse'],
  ['Medication', '/admin/medication', 'Pill'],
  ['Feeding', '/admin/feeding', 'Utensils'],
  ['Inventory', '/admin/inventory', 'Boxes'],
  ['Incidents', '/admin/incidents', 'ShieldAlert'],
  ['Follow-ups', '/admin/followups', 'ListChecks'],
  ['Calendar', '/admin/calendar', 'CalendarDays'],
  ['Recurring Visits', '/admin/recurring-visits', 'Repeat'],
  ['Training', '/admin/training', 'GraduationCap'],
  ['Announcements', '/admin/announcements', 'Megaphone'],
  ['Donations', '/admin/donations', 'Heart'],
  ['Donors', '/admin/donors', 'HeartHandshake'],
  ['Campaigns', '/admin/campaigns', 'Target'],
  ['Expenses', '/admin/expenses', 'Receipt'],
  ['Budgets', '/admin/budgets', 'Wallet'],
  ['Blog Posts', '/admin/blog', 'BookOpen'],
  ['Gallery', '/admin/gallery', 'FileImage'],
  ['Team', '/admin/team', 'Users'],
  ['Craft Shop', '/admin/crafts', 'Package'],
  ['Users', '/admin/users', 'Users'],
  ['Audit Logs', '/admin/audit-logs', 'History'],
  ['Sessions', '/admin/sessions', 'Laptop'],
  ['Settings', '/admin/settings', 'Settings'],
  ['Operations Map', '/admin/operations-map', 'Map'],
  ['Smart Matching', '/admin/matching', 'Sparkles'],
  ['Consents', '/admin/consents', 'FileCheck'],
  ['Family Access', '/admin/family-access', 'Link2'],
  ['Imports', '/admin/imports', 'Upload'],
]
const icons = {
  LayoutDashboard, Heart, HeartPulse, HeartHandshake, Home, Pill, FileImage, Users, Package, Inbox, UserRound,
  ClipboardCheck, Utensils, Boxes, Activity, HandHeart, ShieldAlert, FileBarChart, Gauge, ListChecks, CalendarDays,
  Settings: SettingsIcon, BookOpen, Repeat, GraduationCap, Megaphone, MessageSquare, Layers, Wallet, Target, Receipt,
  ShieldCheck, History, Laptop, Map, Sparkles, FileCheck, Link2, Upload, Bot, TrendingUp,
}

function useNavCounts() {
  const [counts, setCounts] = useState({ requests: 0, messages: 0, directMessages: 0 })
  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        // One shared 60s poll for every nav badge — direct-message unread
        // count included alongside the pre-existing calls rather than a
        // second timer, so this Shell never runs two independent polls.
        const [dash, inbox, unread] = await Promise.all([
          apiFetch('/api/analytics/dashboard'),
          apiFetch('/api/admin/inbox?per_page=1&unread_only=true'),
          apiFetch('/api/messages/unread-count'),
        ])
        if (cancelled) return
        const hc = dash.dashboard.home_community
        setCounts({
          requests: (hc.home_visits_pending || 0) + (hc.assistance_pending || 0),
          messages: inbox.pagination?.total || 0,
          directMessages: unread.unread_count || 0,
        })
      } catch { /* nav badges are a nice-to-have — a failed fetch just leaves them at 0 */ }
    }
    load()
    const interval = setInterval(load, 60000)
    return () => { cancelled = true; clearInterval(interval) }
  }, [])
  return counts
}

function NavBadge({ count }) {
  if (!count) return null
  return <span className="badge-dot bg-red-500 text-white">{count > 99 ? '99+' : count}</span>
}

function NavItem({ label, to, icon, badgeKey, counts, onClick, end }) {
  const Icon = icons[icon] || LayoutDashboard
  return <NavLink
    end={end}
    to={to}
    onClick={onClick}
    className={({ isActive }) => `admin-nav-link flex shrink-0 items-center gap-2 whitespace-nowrap rounded-lg px-3 py-2 text-sm font-semibold transition ${isActive ? 'is-active' : 'text-white/70 hover:bg-white/10 hover:text-white'}`}
  >
    <Icon size={16} /> {label}
    {badgeKey && <NavBadge count={counts[badgeKey]} />}
  </NavLink>
}

function AvatarMenu({ user, onSignOut }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)
  useEffect(() => {
    if (!open) return
    function onClick(e) { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [open])
  const initials = (user?.name || 'A').split(' ').map(p => p[0]).slice(0, 2).join('').toUpperCase()

  return <div className="relative" ref={ref}>
    <button onClick={() => setOpen(o => !o)} className="flex items-center gap-2 rounded-xl px-2 py-1.5 text-left hover:bg-white/10">
      <div className="grid h-9 w-9 place-items-center rounded-full bg-blue-600 text-sm font-bold text-white">{initials}</div>
      <div className="hidden sm:block">
        <div className="text-sm font-semibold leading-tight text-white">{user?.name || 'Admin'}</div>
        <div className="text-xs capitalize leading-tight text-white/50">{user?.role === 'admin' ? 'Super Admin' : (user?.role || 'Staff')}</div>
      </div>
      <ChevronDown size={14} className={`text-white/50 transition ${open ? 'rotate-180' : ''}`} />
    </button>
    {open && <div className="absolute right-0 z-40 mt-2 w-56 overflow-hidden rounded-2xl border border-kBorderSoft bg-kSurface py-2 text-kInk shadow-soft dark:shadow-none">
      <div className="border-b border-kBorderSoft px-4 py-3">
        <div className="text-sm font-semibold text-kInk">{user?.name}</div>
        <div className="truncate text-xs text-kMuted">{user?.email}</div>
      </div>
      <div className="flex items-center justify-between px-4 py-3 text-sm font-semibold"><span>Theme</span><ThemeToggle /></div>
      <Link to="/" className="flex items-center gap-3 px-4 py-2.5 text-sm font-semibold hover:bg-kTint"><LogOut size={15} /> Back to website</Link>
      <button onClick={onSignOut} className="flex w-full items-center gap-3 px-4 py-2.5 text-left text-sm font-semibold text-red-500 hover:bg-kTint"><LogOut size={15} /> Sign out</button>
    </div>}
  </div>
}

export default function Shell({ children }) {
  const navigate = useNavigate()
  const user = getStoredUser()
  const counts = useNavCounts()
  const [moreOpen, setMoreOpen] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const moreRef = useRef(null)

  useEffect(() => {
    if (!moreOpen) return
    function onClick(e) { if (moreRef.current && !moreRef.current.contains(e.target)) setMoreOpen(false) }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [moreOpen])

  async function signOut() { await endSession(); navigate('/admin/login') }

  return <div className="admin-shell min-h-screen bg-kBg">
    <div className="admin-chrome sticky top-0 z-40 border-b border-white/10">
      <header>
        <div className="flex items-center gap-4 px-4 py-3 lg:px-6">
          <button onClick={() => setDrawerOpen(true)} className="grid h-9 w-9 shrink-0 place-items-center rounded-lg text-white/70 hover:bg-white/10 lg:hidden"><Menu size={20} /></button>

          <Link to="/admin" className="flex shrink-0 items-center gap-3">
            <img src="/images/logo.png" alt="KDCCE" className="h-10 w-10 rounded-lg bg-white object-contain p-1" />
            <div className="hidden sm:block">
              <div className="flex items-center gap-1.5 font-display text-base font-bold text-white">Admin Command Center <BadgeCheck size={15} className="text-blue-400" /></div>
              <div className="text-xs text-white/50">Empowering care. Enriching lives.</div>
            </div>
          </Link>

          <div className="ml-auto flex items-center gap-1.5 sm:gap-2">
            <GlobalSearch />
            <NotificationBell variant="dark" />
            <div className="hidden md:block"><QuickActionMenu /></div>
            <div className="h-6 w-px bg-white/10" />
            <AvatarMenu user={user} onSignOut={signOut} />
          </div>
        </div>
        <div className="px-4 pb-3 md:hidden"><QuickActionMenu /></div>
      </header>

      <nav className="hidden border-t border-white/10 lg:block">
        <div className="flex items-center gap-1 overflow-x-auto px-4 py-2 lg:px-6" style={{ scrollbarWidth: 'thin' }}>
          {primaryMenu.map(([label, to, icon, end, badgeKey]) => <NavItem key={to} label={label} to={to} icon={icon} end={end} badgeKey={badgeKey} counts={counts} />)}
          <div className="relative shrink-0" ref={moreRef}>
            <button onClick={() => setMoreOpen(o => !o)} className={`flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-semibold transition ${moreOpen ? 'bg-white/10 text-white' : 'text-white/70 hover:bg-white/10 hover:text-white'}`}>
              More <ChevronDown size={14} className={`transition ${moreOpen ? 'rotate-180' : ''}`} />
            </button>
            {moreOpen && <div className="absolute left-0 z-40 mt-2 grid w-64 grid-cols-1 gap-0.5 overflow-hidden rounded-2xl border border-kBorderSoft bg-kSurface p-2 text-kInk shadow-soft dark:shadow-none">
              {secondaryMenu.map(([label, to, icon]) => { const Icon = icons[icon] || LayoutDashboard; return <NavLink key={to} to={to} onClick={() => setMoreOpen(false)} className={({ isActive }) => `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold ${isActive ? 'bg-blue-500/10 text-blue-500' : 'hover:bg-kTint'}`}><Icon size={16} /> {label}</NavLink> })}
            </div>}
          </div>
        </div>
      </nav>
    </div>

    {/* Mobile / tablet nav drawer — the full menu (primary + secondary),
        since there's no horizontal bar to hold them below lg. */}
    {drawerOpen && <div className="fixed inset-0 z-50 lg:hidden">
      <div className="absolute inset-0 bg-black/60" onClick={() => setDrawerOpen(false)} />
      <div className="admin-chrome absolute inset-y-0 left-0 w-72 overflow-y-auto border-r border-white/10 p-4">
        <div className="mb-4 flex items-center justify-between">
          <img src="/images/logo.png" alt="KDCCE" className="h-9 w-9 rounded-lg bg-white object-contain p-1" />
          <button onClick={() => setDrawerOpen(false)} className="grid h-9 w-9 place-items-center rounded-lg text-white/70 hover:bg-white/10"><X size={18} /></button>
        </div>
        <div className="grid gap-1">
          {primaryMenu.map(([label, to, icon, end, badgeKey]) => <NavItem key={to} label={label} to={to} icon={icon} end={end} badgeKey={badgeKey} counts={counts} onClick={() => setDrawerOpen(false)} />)}
        </div>
        <div className="mt-4 border-t border-white/10 pt-4 text-xs font-bold uppercase tracking-wide text-white/40">More</div>
        <div className="mt-1 grid gap-1">
          {secondaryMenu.map(([label, to, icon]) => <NavItem key={to} label={label} to={to} icon={icon} onClick={() => setDrawerOpen(false)} />)}
        </div>
      </div>
    </div>}

    <main className="container-k py-8">{children}</main>
  </div>
}
