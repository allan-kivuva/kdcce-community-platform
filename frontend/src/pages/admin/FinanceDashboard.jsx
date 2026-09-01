import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { AlertTriangle, Heart, Receipt, Target, Users, Wallet } from 'lucide-react'
import Shell from '../../components/admin/Shell'
import StatCard from '../../components/admin/StatCard'
import StatusBadge from '../../components/admin/StatusBadge'
import { LoadingState, ErrorState, errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch } from '../../lib/api'

function fmtMoney(n) { return `KES ${Number(n || 0).toLocaleString()}` }
function monthBounds() {
  const now = new Date()
  const start = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10)
  return { start, end: now.toISOString().slice(0, 10) }
}

function ProgressBar({ percent, tone = 'bg-kGreen' }) {
  return <div className="h-2 w-full overflow-hidden rounded-full bg-kBorderSoft"><div className={`h-full rounded-full ${tone}`} style={{ width: `${Math.min(percent ?? 0, 100)}%` }} /></div>
}

function useFinanceData() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const { start, end } = monthBounds()
      const [donationsMonth, expensesMonth, campaigns, budgets, donors, recentDonations, recentExpenses] = await Promise.all([
        apiFetch(`/api/reports/donations?date_from=${start}&date_to=${end}`),
        apiFetch(`/api/reports/expenses?date_from=${start}&date_to=${end}`),
        apiFetch('/api/reports/campaigns'),
        apiFetch('/api/reports/budgets'),
        apiFetch('/api/reports/donors'),
        apiFetch('/api/donations'),
        apiFetch('/api/expenses'),
      ])
      setData({
        donationsMonthTotal: donationsMonth.report.cash_total,
        expensesMonthTotal: expensesMonth.report.total_amount,
        campaigns: campaigns.report,
        budgets: budgets.report,
        donorCount: donors.report.donor_count,
        recentDonations: recentDonations.donations.slice(0, 5),
        recentExpenses: recentExpenses.expenses.slice(0, 5),
      })
    } catch (err) { setError(errorMessage(err)) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])
  return { data, loading, error, reload: load }
}

export default function FinanceDashboard() {
  const { data, loading, error, reload } = useFinanceData()

  if (loading) return <Shell><LoadingState label="finance dashboard" /></Shell>
  if (error) return <Shell><ErrorState message={error} onRetry={reload} /></Shell>

  const activeCampaigns = data.campaigns.campaigns.filter(c => c.status === 'Active')
  const totalBudgetRemaining = data.budgets.total_allocated - data.budgets.total_spent

  return <Shell>
    <div><div className="eyebrow">Finance</div><h1 className="font-display text-3xl font-bold text-kGreen">Finance Overview</h1></div>

    <div className="mt-7 grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
      <StatCard icon={Heart} tone="green" label="Donations This Month" value={fmtMoney(data.donationsMonthTotal)} />
      <StatCard icon={Target} tone="purple" label="Active Campaigns" value={activeCampaigns.length} />
      <StatCard icon={Receipt} tone="orange" label="Expenses This Month" value={fmtMoney(data.expensesMonthTotal)} />
      <StatCard icon={Wallet} tone="blue" label="Budget Remaining" value={fmtMoney(totalBudgetRemaining)} subtitle={`of ${fmtMoney(data.budgets.total_allocated)} allocated`} />
      <StatCard icon={Users} tone="cyan" label="Total Donors" value={data.donorCount} />
    </div>

    <div className="mt-6 grid gap-6 xl:grid-cols-2">
      <div className="card-k p-6">
        <div className="flex items-center justify-between"><h2 className="font-display text-lg font-bold text-kInk">Campaign Progress</h2><Link to="/admin/campaigns" className="text-sm font-semibold text-kOrange">View all</Link></div>
        <div className="mt-4 grid gap-4">
          {data.campaigns.campaigns.slice(0, 5).map(c => <div key={c.id}>
            <div className="flex items-center justify-between text-sm"><span className="font-semibold text-kInk">{c.name}</span><span className="text-xs text-kMuted">{c.percent_achieved ?? 0}%</span></div>
            <div className="mt-1.5"><ProgressBar percent={c.percent_achieved} /></div>
          </div>)}
          {data.campaigns.campaigns.length === 0 && <p className="py-6 text-center text-sm text-kMuted">No campaigns yet.</p>}
        </div>
      </div>

      <div className="card-k p-6">
        <div className="flex items-center justify-between"><h2 className="font-display text-lg font-bold text-kInk">Budget Overview</h2><Link to="/admin/budgets" className="text-sm font-semibold text-kOrange">View all</Link></div>
        <div className="mt-4 grid gap-4">
          {data.budgets.budgets.slice(0, 5).map(b => <div key={b.id}>
            <div className="flex items-center justify-between text-sm">
              <span className="font-semibold text-kInk">{b.program_name}</span>
              <span className="flex items-center gap-1 text-xs text-kMuted">{b.warning_level && <AlertTriangle size={11} className="text-red-500" />}{fmtMoney(b.spent)} / {fmtMoney(b.allocated_amount)}</span>
            </div>
            <div className="mt-1.5"><ProgressBar percent={(b.spent / (b.allocated_amount || 1)) * 100} tone={b.warning_level === 'exceeded' ? 'bg-red-500' : b.warning_level ? 'bg-amber-500' : 'bg-kGreen'} /></div>
          </div>)}
          {data.budgets.budgets.length === 0 && <p className="py-6 text-center text-sm text-kMuted">No budgets yet.</p>}
        </div>
      </div>
    </div>

    <div className="mt-6 grid gap-6 xl:grid-cols-2">
      <div className="card-k p-6">
        <div className="flex items-center justify-between"><h2 className="font-display text-lg font-bold text-kInk">Recent Donations</h2><Link to="/admin/donations" className="text-sm font-semibold text-kOrange">View all</Link></div>
        <div className="mt-4 grid gap-1">
          {data.recentDonations.map(d => <div key={d.id} className="flex items-center justify-between border-b border-kBorderSoft py-2.5 last:border-0">
            <div><div className="text-sm font-semibold text-kInk">{d.donor_name}</div><div className="text-xs text-kMuted">{new Date(d.created_at).toLocaleDateString([], { dateStyle: 'medium' })}</div></div>
            <div className="text-right"><div className="text-sm font-bold text-kGreen">{d.donation_type === 'Cash' ? fmtMoney(d.amount) : d.donation_type}</div><StatusBadge value={d.status} /></div>
          </div>)}
          {data.recentDonations.length === 0 && <p className="py-6 text-center text-sm text-kMuted">No donations yet.</p>}
        </div>
      </div>

      <div className="card-k p-6">
        <div className="flex items-center justify-between"><h2 className="font-display text-lg font-bold text-kInk">Recent Expenses</h2><Link to="/admin/expenses" className="text-sm font-semibold text-kOrange">View all</Link></div>
        <div className="mt-4 grid gap-1">
          {data.recentExpenses.map(e => <div key={e.id} className="flex items-center justify-between border-b border-kBorderSoft py-2.5 last:border-0">
            <div><div className="text-sm font-semibold text-kInk">{e.category}{e.program_name ? ` · ${e.program_name}` : ''}</div><div className="text-xs text-kMuted">{new Date(e.expense_date).toLocaleDateString([], { dateStyle: 'medium' })}</div></div>
            <div className="text-right"><div className="text-sm font-bold text-kOrange">{fmtMoney(e.amount)}</div><StatusBadge value={e.status} /></div>
          </div>)}
          {data.recentExpenses.length === 0 && <p className="py-6 text-center text-sm text-kMuted">No expenses yet.</p>}
        </div>
      </div>
    </div>
  </Shell>
}
