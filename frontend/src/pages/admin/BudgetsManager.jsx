import { useState, useEffect } from 'react'
import { AlertTriangle, Plus, Wallet } from 'lucide-react'
import Shell from '../../components/admin/Shell'
import Modal from '../../components/admin/Modal'
import { LoadingState, ErrorState, EmptyState, errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch } from '../../lib/api'
import { useApiResource } from '../../lib/useApiResource'

function fmtMoney(n) { return `KES ${Number(n || 0).toLocaleString()}` }

const WARNING_STYLES = {
  warning: 'bg-amber-500/10 text-amber-600 border-amber-200',
  alert: 'bg-orange-500/10 text-orange-600 border-orange-200',
  exceeded: 'bg-red-500/10 text-red-600 border-red-200',
}
const WARNING_LABELS = { warning: '75%+ used', alert: '90%+ used', exceeded: 'Over budget' }

function ProgressBar({ percent, warningLevel }) {
  const pct = Math.min(percent ?? 0, 100)
  const color = warningLevel === 'exceeded' ? 'bg-red-500' : warningLevel === 'alert' ? 'bg-orange-500' : warningLevel === 'warning' ? 'bg-amber-500' : 'bg-kGreen'
  return <div className="h-2.5 w-full overflow-hidden rounded-full bg-kBorderSoft"><div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} /></div>
}

function BudgetFormModal({ onClose, onSaved, showToast }) {
  const [saving, setSaving] = useState(false)
  const [programs, setPrograms] = useState([])
  useEffect(() => { apiFetch('/api/programs').then(d => setPrograms(d.programs)).catch(() => {}) }, [])

  async function save(e) {
    e.preventDefault()
    const f = new FormData(e.target)
    setSaving(true)
    try {
      await apiFetch('/api/budgets', {
        method: 'POST',
        body: {
          program_id: Number(f.get('program_id')), allocated_amount: Number(f.get('allocated_amount')),
          period_start: f.get('period_start') || null, period_end: f.get('period_end') || null,
          notes: f.get('notes') || null,
        },
      })
      showToast('Budget created')
      onSaved()
      onClose()
    } catch (err) { showToast(errorMessage(err)) }
    finally { setSaving(false) }
  }

  return <Modal title="New budget" onClose={onClose}>
    <form onSubmit={save} className="grid gap-4">
      <label className="text-sm font-semibold">Program<select name="program_id" className="input-k mt-2" required><option value="">Choose a program…</option>{programs.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
      <label className="text-sm font-semibold">Allocated amount (KES)<input name="allocated_amount" type="number" min="0" step="0.01" className="input-k mt-2" required /></label>
      <div className="grid grid-cols-2 gap-4">
        <label className="text-sm font-semibold">Period start<input name="period_start" type="date" className="input-k mt-2" /></label>
        <label className="text-sm font-semibold">Period end<input name="period_end" type="date" className="input-k mt-2" /></label>
      </div>
      <label className="text-sm font-semibold">Notes<textarea name="notes" rows={2} className="input-k mt-2" /></label>
      <button disabled={saving} className="btn-orange mt-2 disabled:opacity-60">{saving ? 'Saving…' : 'Create budget'}</button>
    </form>
  </Modal>
}

export default function BudgetsManager({ showToast }) {
  const budgetsApi = useApiResource('/api/budgets', { listKey: 'budgets', itemKey: 'budget' })
  const [creating, setCreating] = useState(false)

  return <Shell>
    <div className="flex items-center justify-between">
      <div><div className="eyebrow">Finance</div><h1 className="font-display text-3xl font-bold text-kGreen">Program Budgets</h1></div>
      <button onClick={() => setCreating(true)} className="btn-orange"><Plus size={16} /> New budget</button>
    </div>

    <div className="mt-7">
      {budgetsApi.loading && <LoadingState label="budgets" />}
      {!budgetsApi.loading && budgetsApi.error && <ErrorState message={budgetsApi.error} onRetry={budgetsApi.reload} />}
      {!budgetsApi.loading && !budgetsApi.error && budgetsApi.items.length === 0 && <EmptyState icon={Wallet} title="No budgets yet" message="Allocate a budget to a program to start tracking spend." />}
      {!budgetsApi.loading && !budgetsApi.error && budgetsApi.items.length > 0 && <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {budgetsApi.items.map(b => <div key={b.id} className={`card-k p-5 ${b.warning_level ? `border ${WARNING_STYLES[b.warning_level]}` : ''}`}>
          <div className="flex items-center justify-between gap-2">
            <span className="font-semibold text-kInk">{b.program_name}</span>
            {b.warning_level && <span className="flex items-center gap-1 text-[10px] font-bold uppercase text-red-500"><AlertTriangle size={11} /> {WARNING_LABELS[b.warning_level]}</span>}
          </div>
          {(b.period_start || b.period_end) && <div className="mt-0.5 text-xs text-kMuted">{b.period_start || '—'} to {b.period_end || '—'}</div>}
          <div className="mt-4 flex items-baseline justify-between text-sm"><span className="font-bold text-kGreen">{fmtMoney(b.spent)}</span><span className="text-xs text-kMuted">of {fmtMoney(b.allocated_amount)}</span></div>
          <div className="mt-2"><ProgressBar percent={b.percent_used} warningLevel={b.warning_level} /></div>
          <div className="mt-2 flex items-center justify-between text-xs text-kMuted"><span>{b.percent_used ?? 0}% used</span><span className="font-semibold text-kInk">{fmtMoney(b.remaining)} left</span></div>
        </div>)}
      </div>}
    </div>

    {creating && <BudgetFormModal onClose={() => setCreating(false)} onSaved={budgetsApi.reload} showToast={showToast} />}
  </Shell>
}
