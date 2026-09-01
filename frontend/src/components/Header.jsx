import { useState } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { Heart, Menu, X, ChevronDown } from 'lucide-react'
import { PrimaryButton } from './Button'
import ThemeToggle from '../theme/ThemeToggle'

const nav = [
  ['Home', '/'],
  ['About Us', '/about'],
  ['Programs', '/programs'],
  ['Campaigns', '/campaigns'],
  ['Impact', '/about#impact'],
  ['Gallery', '/gallery'],
  ['Get Involved', '/sponsor'],
  ['Contact', '/contact']
]

export default function Header() {
  const [open, setOpen] = useState(false)
  return (
    <header className="sticky top-0 z-50 bg-kSurface/95 backdrop-blur glass-nav">
      <div className="container-k flex min-h-[82px] items-center justify-between gap-6 py-2">
        <Link to="/" className="flex items-center" onClick={() => setOpen(false)} aria-label="KDCCE home">
          <img src="/images/logo.png" alt="Kibera Day Care Centre for the Elderly" className="h-[66px] w-auto max-w-[210px] object-contain object-left" />
        </Link>

        <nav className="hidden items-center gap-7 lg:flex">
          {nav.map(([label, to]) => (
            <NavLink key={label} to={to} className={({ isActive }) => `relative text-[13px] font-semibold ${isActive ? 'text-kOrange' : 'text-kInk'} transition`}>
              {label}
              {label === 'Get Involved' && <ChevronDown className="ml-1 inline h-3 w-3" />}
            </NavLink>
          ))}
        </nav>

        <div className="hidden items-center gap-3 lg:flex">
          <ThemeToggle />
          <PrimaryButton to="/donate"><Heart className="h-4 w-4" fill="currentColor" /> Donate Now</PrimaryButton>
        </div>
        <div className="flex items-center gap-2 lg:hidden">
          <ThemeToggle />
          <button className="grid h-10 w-10 place-items-center rounded-xl border border-kBorder text-kInk lg:hidden" onClick={() => setOpen(!open)} aria-label="Toggle menu">
            {open ? <X /> : <Menu />}
          </button>
        </div>
      </div>
      {open && (
        <div className="border-t border-kBorderSoft bg-kSurface px-5 pb-5 lg:hidden">
          <div className="mx-auto flex max-w-[1180px] flex-col gap-2 pt-3">
            {nav.map(([label, to]) => <Link key={label} onClick={() => setOpen(false)} to={to} className="rounded-lg px-3 py-3 font-semibold text-kInk hover:bg-kTint">{label}</Link>)}
            <PrimaryButton to="/donate" className="mt-2"><Heart className="h-4 w-4" /> Donate Now</PrimaryButton>
          </div>
        </div>
      )}
    </header>
  )
}
