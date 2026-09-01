import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Activity, BookOpen, ChevronDown, HandHeart, Heart, HeartHandshake, Home, Megaphone, MessageSquarePlus, Package,
  Plus, Receipt, ShieldAlert, Target, UserRound,
} from 'lucide-react'

// Every entry here deep-links to a manager page that already has its own
// "+ Add" button/modal (ElderlyManager, HomeVisitManager, ...) — same
// pattern the old inline QuickActionMenu in AdminDashboard.jsx already
// used for donations/blog/crafts, just extended to the rest of what the
// backend actually supports creating. Deliberately NOT listed: "Add
// volunteer" (volunteers self-register; admin/staff can only review an
// application — see /admin/volunteers).
const ACTIONS = [
  { label: 'Register elderly member', to: '/admin/elderly', icon: UserRound },
  { label: 'Create home visit', to: '/admin/home-visits', icon: Home },
  { label: 'Create assistance request', to: '/admin/assistance', icon: HandHeart },
  { label: 'Report a concern', to: '/admin/incidents', icon: ShieldAlert },
  { label: 'Send a message', to: '/admin/messages', icon: MessageSquarePlus },
  { label: 'Send announcement', to: '/admin/announcements', icon: Megaphone },
  { label: 'Log a donation', to: '/admin/donations', icon: Heart },
  { label: 'Record expense', to: '/admin/expenses', icon: Receipt },
  { label: 'New campaign', to: '/admin/campaigns', icon: Target },
  { label: 'Create activity', to: '/admin/activities', icon: Activity },
  { label: 'Review volunteer applications', to: '/admin/volunteers', icon: HeartHandshake },
  { label: 'New blog post', to: '/admin/blog', icon: BookOpen },
  { label: 'Add craft item', to: '/admin/crafts', icon: Package },
]

export default function QuickActionMenu() {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    if (!open) return
    function onClick(e) { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    function onKey(e) { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('mousedown', onClick)
    document.addEventListener('keydown', onKey)
    return () => { document.removeEventListener('mousedown', onClick); document.removeEventListener('keydown', onKey) }
  }, [open])

  return <div className="relative" ref={ref}>
    <button onClick={() => setOpen(o => !o)} className="flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-bold text-white transition hover:bg-blue-700">
      <Plus size={16} /> Quick Action <ChevronDown size={14} className={`transition ${open ? 'rotate-180' : ''}`} />
    </button>
    {open && <div className="absolute right-0 z-40 mt-2 w-64 overflow-hidden rounded-2xl border border-kBorderSoft bg-kSurface py-2 text-kInk shadow-soft dark:shadow-none">
      {ACTIONS.map(({ label, to, icon: Icon }) => <Link key={to + label} to={to} onClick={() => setOpen(false)} className="flex items-center gap-3 px-4 py-2.5 text-sm font-semibold hover:bg-kTint">
        <Icon size={16} className="text-blue-500" /> {label}
      </Link>)}
    </div>}
  </div>
}
