import { useEffect, useRef, useState } from 'react'
import { Sun, Moon, Monitor, Check } from 'lucide-react'
import { useTheme } from './ThemeProvider'

const options = [
  { value: 'light', label: 'Light', icon: Sun },
  { value: 'dark', label: 'Dark', icon: Moon },
  { value: 'system', label: 'System', icon: Monitor }
]

export default function ThemeToggle({ variant = 'light' }) {
  const { preference, resolved, setPreference } = useTheme()
  const [open, setOpen] = useState(false)
  const ref = useRef(null)
  const ActiveIcon = options.find(o => o.value === preference)?.icon || Monitor

  useEffect(() => {
    function onClick(e) { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    function onKey(e) { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('mousedown', onClick)
    document.addEventListener('keydown', onKey)
    return () => { document.removeEventListener('mousedown', onClick); document.removeEventListener('keydown', onKey) }
  }, [])

  const isDarkSurface = variant === 'dark'

  return <div className="relative" ref={ref}>
    <button
      onClick={() => setOpen(o => !o)}
      aria-label={`Theme: ${preference} (currently ${resolved}). Click to change.`}
      aria-expanded={open}
      className={`grid h-10 w-10 place-items-center rounded-xl border transition ${isDarkSurface ? 'border-white/15 text-white/80 hover:bg-white/10' : 'border-kBorder text-kMuted hover:bg-kTint hover:text-kOrange'}`}
    >
      <ActiveIcon size={18} />
    </button>
    {open && <div className={`absolute right-0 z-50 mt-2 w-40 overflow-hidden rounded-xl border shadow-soft ${isDarkSurface ? 'border-white/10 bg-[#0b1721] text-white' : 'border-kBorderSoft bg-kSurface text-kInk'}`}>
      {options.map(({ value, label, icon: Icon }) => <button
        key={value}
        onClick={() => { setPreference(value); setOpen(false) }}
        className={`flex w-full items-center gap-3 px-4 py-3 text-left text-sm font-semibold transition hover:bg-kTint hover:text-kOrange ${isDarkSurface ? 'hover:bg-white/10 hover:text-white' : ''} ${preference === value ? 'text-kOrange' : ''}`}
      >
        <Icon size={16} /> {label}
        {preference === value && <Check size={14} className="ml-auto" />}
      </button>)}
    </div>}
  </div>
}
