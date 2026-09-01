import { useState, useEffect } from 'react'
import { Plus, Receipt } from 'lucide-react'
import Shell from '../../components/admin/Shell'
import Modal from '../../components/admin/Modal'
import DataTable from '../../components/admin/DataTable'
import StatusBadge from '../../components/admin/StatusBadge'
import { errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch, downloadFile, getStoredUser, uploadForm } from '../../lib/api'
import { useApiResource } from '../../lib/useApiResource'

const CATEGORIES = ['Food', 'Medical', 'Transport', 'Utilities', 'Program Supplies', 'Events', 'Maintenance', 'Administration', 'Other']

function fmtMoney(n) { return `KES ${Number(n || 0).toLocaleString()}` }

function ExpenseFormModal({ onClose, onSaved, showToast }) {
  const [saving, setSaving] = useState(false)
  const [programs, setPrograms] = useState([])
  useEffect(() => { apiFetch('/api/programs').then(d => setPrograms(d.programs)).catch(() => {}) }, [])

  async function save(e) {
    e.preventDefault()
    const f = new FormData(e.target)
    if (!f.get('program_id')) f.delete('program_id')
    if (!f.get('vendor_name')) f.delete('vendor_name')
    if (!f.get('file') || !f.get('file').name) f.delete('file')
    setSaving(true)
    try { await uploadForm('/api/expenses', f); showToast('Expense recorded'); onSaved(); onClose() }
    catch (err) { showToast(errorMessage(err)) }
    finally { setSaving(false) }
  }

  return <Modal title="Record expense" onClose={onClose}>
    <form onSubmit={save} className="grid gap-4">
      <div className="grid grid-cols-2 gap-4">
        <label className="text-sm font-semibold">Amount (KES)<input name="amount" type="number" min="0.01" step="0.01" className="input-k mt-2" required /></label>
        <label className="text-sm font-semibold">Category<select name="category" defaultValue="Food" className="input-k mt-2">{CATEGORIES.map(c => <option key={c}>{c}</option>)}</select></label>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <label className="text-sm font-semibold">Date<input name="expense_date" type="date" defaultValue={new Date().toISOString().slice(0, 10)} className="input-k mt-2" required /></label>
        <label className="text-sm font-semibold">Vendor (optional)<input name="vendor_name" className="input-k mt-2" /></label>
      </div>
      <label className="text-sm font-semibold">Program (optional)<select name="program_id" className="input-k mt-2"><option value="">Unassigned</option>{programs.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
      <label className="text-sm font-semibold">Description<textarea name="description" rows={2} className="input-k mt-2" /></label>
      <label className="text-sm font-semibold">Receipt (optional)<input name="file" type="file" accept="image/jpeg,image/png,image/webp,application/pdf" className="input-k mt-2" /></label>
      <button disabled={saving} className="btn-orange mt-2 disabled:opacity-60">{saving ? 'Saving…' : 'Record expense'}</button>
    </form>
  </Modal>
}

export default function ExpensesManager({ showToast }) {
  const expensesApi = useApiResource('/api/expenses', { listKey: 'expenses', itemKey: 'expense' })
  const [creating, setCreating] = useState(false)
  const [statusFilter, setStatusFilter] = useState('All')
  const me = getStoredUser()

  const filtered = expensesApi.items.filter(e => statusFilter === 'All' || e.status === statusFilter)

  async function setStatus(expense, status) {
    try { await expensesApi.patch(expense.id, { status }); showToast(`Expense ${status.toLowerCase()}`) }
    catch (err) { showToast(errorMessage(err)) }
  }

  async function viewReceipt(expense) {
    try { await downloadFile(`/api/expenses/${expense.id}/receipt`, `receipt-${expense.id}.pdf`) }
    catch (err) { showToast(errorMessage(err)) }
  }

  const columns = [
    { key: 'expense_date', label: 'Date', sortable: true, render: e => <span className="text-kMuted">{new Date(e.expense_date).toLocaleDateString([], { dateStyle: 'medium' })}</span> },
    { key: 'category', label: 'Category', sortable: true, render: e => <span className="text-kInk">{e.category}</span> },
    { key: 'amount', label: 'Amount', sortable: true, render: e => <span className="font-semibold text-kInk">{fmtMoney(e.amount)}</span> },
    { key: 'program_name', label: 'Program', render: e => <span className="text-kMuted">{e.program_name || '—'}</span> },
    { key: 'vendor_name', label: 'Vendor', render: e => <span className="text-kMuted">{e.vendor_name || '—'}</span> },
    { key: 'status', label: 'Status', sortable: true, render: e => <StatusBadge value={e.status} /> },
    { key: 'action', label: 'Action', render: e => <div className="flex items-center gap-2">
      {e.document_id && <button onClick={() => viewReceipt(e)} className="text-kOrange" title="Download receipt"><Receipt size={15} /></button>}
      {e.status === 'Recorded' && me?.role === 'admin' && <>
        <button onClick={() => setStatus(e, 'Approved')} className="text-xs font-bold text-emerald-600">Approve</button>
        <button onClick={() => setStatus(e, 'Rejected')} className="text-xs font-bold text-red-600">Reject</button>
      </>}
      {(e.status === 'Approved' || e.status === 'Recorded') && me?.role === 'admin' && <button onClick={() => setStatus(e, 'Voided')} className="text-xs font-bold text-kMuted">Void</button>}
    </div> },
  ]

  return <Shell>
    <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
      <div><div className="eyebrow">Finance</div><h1 className="font-display text-3xl font-bold text-kGreen">Expenses</h1></div>
      <button onClick={() => setCreating(true)} className="btn-orange"><Plus size={16} /> Record expense</button>
    </div>

    <div className="mt-7">
      <DataTable
        columns={columns} data={filtered} loading={expensesApi.loading} error={expensesApi.error} onRetry={expensesApi.reload}
        emptyMessage="No expenses match your filter." minWidth={900}
        header={<select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="rounded-xl border border-kBorder bg-kSurface px-4 py-3 text-sm text-kInk"><option>All</option><option>Recorded</option><option>Approved</option><option>Rejected</option><option>Voided</option></select>}
      />
    </div>

    {creating && <ExpenseFormModal onClose={() => setCreating(false)} onSaved={expensesApi.reload} showToast={showToast} />}
  </Shell>
}
