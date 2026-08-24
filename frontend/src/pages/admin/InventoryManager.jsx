import { useState, useEffect, useCallback } from 'react'
import { Search, Plus, AlertTriangle, ArrowDownCircle, ArrowUpCircle } from 'lucide-react'
import Shell from '../../components/admin/Shell'
import Modal from '../../components/admin/Modal'
import { LoadingState, ErrorState, errorMessage } from '../../components/admin/adminHelpers'
import { useApiResource } from '../../lib/useApiResource'
import { apiFetch } from '../../lib/api'

const CATEGORIES = ['Food', 'Medical', 'Hygiene', 'Equipment', 'Other']

function fmtDate(iso) { return iso ? new Date(iso).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }) : '—' }

function NewItemModal({ onClose, onCreated, showToast }) {
  const [saving, setSaving] = useState(false)
  async function save(e) {
    e.preventDefault()
    const f = new FormData(e.target)
    setSaving(true)
    try {
      await onCreated({ name: f.get('name'), category: f.get('category'), unit: f.get('unit'), minimum_stock: Number(f.get('minimum_stock') || 0), notes: f.get('notes') || null })
      showToast('Item added')
      onClose()
    } catch (err) { showToast(errorMessage(err)) }
    finally { setSaving(false) }
  }
  return <Modal title="Add inventory item" onClose={onClose}>
    <form onSubmit={save} className="grid gap-4">
      <label className="text-sm font-semibold">Name<input name="name" className="input-k mt-2" required /></label>
      <div className="grid grid-cols-2 gap-4">
        <label className="text-sm font-semibold">Category<select name="category" defaultValue="Food" className="input-k mt-2">{CATEGORIES.map(c => <option key={c}>{c}</option>)}</select></label>
        <label className="text-sm font-semibold">Unit<input name="unit" placeholder="kg, boxes..." className="input-k mt-2" required /></label>
      </div>
      <label className="text-sm font-semibold">Minimum stock<input name="minimum_stock" type="number" min="0" step="0.01" defaultValue="0" className="input-k mt-2" /></label>
      <label className="text-sm font-semibold">Notes<textarea name="notes" rows={2} className="input-k mt-2" /></label>
      <button disabled={saving} className="btn-orange mt-2 disabled:opacity-60">{saving ? 'Adding…' : 'Add item'}</button>
    </form>
  </Modal>
}

function MovementModal({ item, movementType, onClose, onDone, showToast }) {
  const [saving, setSaving] = useState(false)
  const isIn = movementType === 'In'
  async function save(e) {
    e.preventDefault()
    const f = new FormData(e.target)
    setSaving(true)
    try {
      await apiFetch(`/api/inventory/${item.id}/movements`, {
        method: 'POST',
        body: { movement_type: movementType, quantity: Number(f.get('quantity')), reason: f.get('reason') || null, expiry_date: isIn ? (f.get('expiry_date') || null) : null },
      })
      showToast(`${isIn ? 'Stock in' : 'Stock out'} recorded`)
      onDone()
      onClose()
    } catch (err) { showToast(errorMessage(err)) }
    finally { setSaving(false) }
  }
  return <Modal title={`${isIn ? 'Stock in' : 'Stock out'} — ${item.name}`} onClose={onClose}>
    <p className="mb-4 text-sm text-kMuted">Current stock: <span className="font-bold text-kInk">{item.current_stock} {item.unit}</span></p>
    <form onSubmit={save} className="grid gap-4">
      <label className="text-sm font-semibold">Quantity ({item.unit})<input name="quantity" type="number" min="0.01" step="0.01" max={isIn ? undefined : item.current_stock} className="input-k mt-2" required /></label>
      {isIn && <label className="text-sm font-semibold">Expiry date (optional)<input name="expiry_date" type="date" className="input-k mt-2" /></label>}
      <label className="text-sm font-semibold">Reason<input name="reason" placeholder={isIn ? 'e.g. Donation received' : 'e.g. Used for lunch service'} className="input-k mt-2" /></label>
      <button disabled={saving} className={`mt-2 disabled:opacity-60 ${isIn ? 'btn-green' : 'btn-orange'}`}>{saving ? 'Saving…' : isIn ? 'Record stock in' : 'Record stock out'}</button>
    </form>
  </Modal>
}

function ItemDetail({ item, onReload, showToast }) {
  const [movements, setMovements] = useState([])
  const [loading, setLoading] = useState(true)
  const [movementType, setMovementType] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    try { setMovements((await apiFetch(`/api/inventory/${item.id}/movements`)).movements) }
    catch (err) { showToast(errorMessage(err)) }
    finally { setLoading(false) }
  }, [item.id, showToast])

  useEffect(() => { load() }, [load])

  return <div className="card-k p-6">
    <div className="flex items-center justify-between"><div><h2 className="font-display text-lg font-bold text-kGreen">{item.name}</h2><p className="text-xs text-kMuted">{item.category}</p></div>{item.low_stock && <span className="flex items-center gap-1 rounded-full bg-kTint px-3 py-1 text-xs font-bold text-kOrange"><AlertTriangle size={13} /> Low stock</span>}</div>
    <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
      <div className="rounded-xl bg-kCream p-4"><div className="text-xs text-kMuted">Current stock</div><div className="mt-1 font-display text-2xl font-bold text-kGreen">{item.current_stock} <span className="text-sm font-normal text-kMuted">{item.unit}</span></div></div>
      <div className="rounded-xl bg-kCream p-4"><div className="text-xs text-kMuted">Minimum stock</div><div className="mt-1 font-display text-2xl font-bold text-kInk">{item.minimum_stock} <span className="text-sm font-normal text-kMuted">{item.unit}</span></div></div>
    </div>
    {item.notes && <p className="mt-4 text-sm text-kMuted">{item.notes}</p>}
    <div className="mt-5 flex gap-2">
      <button onClick={() => setMovementType('In')} className="btn-green flex-1"><ArrowUpCircle size={16} /> Stock in</button>
      <button onClick={() => setMovementType('Out')} className="btn-orange flex-1"><ArrowDownCircle size={16} /> Stock out</button>
    </div>

    <h3 className="mt-6 font-display text-sm font-bold uppercase tracking-wide text-kMuted">History</h3>
    {loading ? <p className="mt-3 text-sm text-kMuted">Loading…</p> : <div className="mt-3 overflow-x-auto"><table className="w-full min-w-[500px] text-left text-sm"><thead className="text-xs uppercase tracking-wider text-kMuted"><tr><th className="py-2">Type</th><th>Qty</th><th>Reason</th><th>By</th><th>Date</th></tr></thead><tbody>
      {movements.map(m => <tr key={m.id} className="border-t border-kBorderSoft"><td className={`py-2 font-semibold ${m.movement_type === 'In' ? 'text-kGreen' : 'text-kOrange'}`}>{m.movement_type}</td><td>{m.quantity}</td><td className="text-kMuted">{m.reason || '—'}</td><td className="text-kMuted">{m.recorded_by}</td><td className="text-kMuted">{fmtDate(m.created_at)}</td></tr>)}
      {movements.length === 0 && <tr><td colSpan={5} className="py-6 text-center text-kMuted">No movements yet.</td></tr>}
    </tbody></table></div>}

    {movementType && <MovementModal item={item} movementType={movementType} onClose={() => setMovementType(null)} onDone={() => { load(); onReload() }} showToast={showToast} />}
  </div>
}

export default function InventoryManager({ showToast }) {
  const itemsApi = useApiResource('/api/inventory', { listKey: 'items', itemKey: 'item' })
  const [q, setQ] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('All')
  const [lowStockOnly, setLowStockOnly] = useState(false)
  const [selectedId, setSelectedId] = useState(null)
  const [newModalOpen, setNewModalOpen] = useState(false)

  const filtered = itemsApi.items.filter(i =>
    (categoryFilter === 'All' || i.category === categoryFilter) &&
    (!lowStockOnly || i.low_stock) &&
    i.name.toLowerCase().includes(q.toLowerCase())
  )
  const selected = itemsApi.items.find(i => i.id === selectedId) || null
  const lowStockCount = itemsApi.items.filter(i => i.low_stock).length

  return <Shell>
    <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
      <div><div className="eyebrow">Manage</div><h1 className="font-display text-3xl font-bold text-kGreen">Inventory</h1></div>
      <button onClick={() => setNewModalOpen(true)} className="btn-green"><Plus size={16} /> Add item</button>
    </div>

    {lowStockCount > 0 && <button onClick={() => setLowStockOnly(true)} className="mt-6 flex w-full items-center gap-2 rounded-xl border-l-4 border-l-kOrange bg-kTint px-5 py-3 text-left text-sm font-semibold text-kOrange"><AlertTriangle size={16} /> {lowStockCount} item{lowStockCount > 1 ? 's' : ''} at or below minimum stock</button>}

    <div className="mt-6 grid gap-6 xl:grid-cols-[1fr_1.1fr]">
      <div>
        <div className="card-k overflow-hidden">
          <div className="flex flex-col gap-3 border-b border-kBorderSoft p-5">
            <div className="relative"><Search className="absolute left-3 top-3.5 text-kMuted" size={17} /><input value={q} onChange={e => setQ(e.target.value)} className="input-k pl-10" placeholder="Search items..." /></div>
            <div className="flex gap-3">
              <select value={categoryFilter} onChange={e => setCategoryFilter(e.target.value)} className="flex-1 rounded-xl border border-kBorder bg-kSurface px-4 py-3 text-sm text-kInk"><option>All</option>{CATEGORIES.map(c => <option key={c}>{c}</option>)}</select>
              <label className="flex items-center gap-2 whitespace-nowrap rounded-xl border border-kBorder px-4 text-sm font-semibold text-kInk"><input type="checkbox" checked={lowStockOnly} onChange={e => setLowStockOnly(e.target.checked)} className="h-4 w-4" /> Low stock</label>
            </div>
          </div>
          {itemsApi.loading ? <LoadingState label="inventory" /> : itemsApi.error ? <ErrorState message={itemsApi.error} onRetry={itemsApi.reload} /> : <div className="grid gap-2 p-4">
            {filtered.map(i => <button key={i.id} onClick={() => setSelectedId(i.id)} className={`flex items-center justify-between rounded-xl border px-4 py-3 text-left ${selectedId === i.id ? 'border-kOrange bg-kTint' : 'border-kBorder hover:bg-kCream'}`}>
              <div><div className="font-semibold text-kInk">{i.name}</div><div className="text-xs text-kMuted">{i.category}</div></div>
              <div className="text-right"><div className={`text-sm font-bold ${i.low_stock ? 'text-kOrange' : 'text-kGreen'}`}>{i.current_stock} {i.unit}</div>{i.low_stock && <div className="text-xs text-kOrange">Low</div>}</div>
            </button>)}
            {filtered.length === 0 && <p className="p-4 text-center text-sm text-kMuted">No items match your filters.</p>}
          </div>}
        </div>
      </div>
      <div>{selected ? <ItemDetail item={selected} onReload={itemsApi.reload} showToast={showToast} /> : <div className="card-k p-10 text-center text-sm text-kMuted">Select an item to view stock history.</div>}</div>
    </div>

    {newModalOpen && <NewItemModal onClose={() => setNewModalOpen(false)} onCreated={data => itemsApi.create(data)} showToast={showToast} />}
  </Shell>
}
