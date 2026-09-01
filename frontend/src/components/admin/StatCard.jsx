import { ArrowDownRight, ArrowUpRight } from 'lucide-react'
import MiniSparkline from './MiniSparkline'

const TONES = {
  blue: { bg: 'bg-blue-500/10', text: 'text-blue-500', line: '#3b82f6' },
  cyan: { bg: 'bg-cyan-500/10', text: 'text-cyan-500', line: '#06b6d4' },
  green: { bg: 'bg-emerald-500/10', text: 'text-emerald-500', line: '#10b981' },
  purple: { bg: 'bg-purple-500/10', text: 'text-purple-500', line: '#a855f7' },
  orange: { bg: 'bg-amber-500/10', text: 'text-amber-500', line: '#f59e0b' },
  red: { bg: 'bg-red-500/10', text: 'text-red-500', line: '#ef4444' },
}

/** trendPct: signed number (e.g. 12.5 or -7.1) or null/undefined when there's
 * nothing to compare against yet — renders no trend rather than a fake one.
 * subtitle: plain-text fallback (e.g. a real breakdown) shown instead of a
 * trend when no day-over-day comparison exists for this metric. */
export default function StatCard({ icon: Icon, label, value, trendPct, trendLabel = 'vs last month', subtitle, tone = 'blue', sparkline }) {
  const t = TONES[tone] || TONES.blue
  const hasTrend = typeof trendPct === 'number' && Number.isFinite(trendPct)
  const isUp = hasTrend && trendPct >= 0

  return <div className="card-k p-5">
    <div className="flex items-center justify-between">
      <div className={`grid h-10 w-10 place-items-center rounded-xl ${t.bg} ${t.text}`}><Icon size={19} /></div>
      {hasTrend && <div className={`flex items-center gap-0.5 text-xs font-bold ${isUp ? 'text-emerald-500' : 'text-red-500'}`}>
        {isUp ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />}{Math.abs(trendPct)}%
      </div>}
    </div>
    <div className="mt-4 text-xs font-semibold uppercase tracking-wide text-kMuted">{label}</div>
    <div className="mt-1 font-display text-3xl font-bold text-kInk">{value}</div>
    {hasTrend ? <div className="mt-1 text-xs text-kMuted">{trendLabel}</div> : subtitle ? <div className="mt-1 text-xs text-kMuted">{subtitle}</div> : null}
    {sparkline && sparkline.length > 1 && <div className="mt-3"><MiniSparkline data={sparkline} color={t.line} /></div>}
  </div>
}
