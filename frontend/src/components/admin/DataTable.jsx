import { useEffect, useMemo, useState } from 'react'
import { ArrowDown, ArrowUp, ArrowUpDown, ChevronLeft, ChevronRight } from 'lucide-react'
import { LoadingState, ErrorState } from './adminHelpers'

/**
 * Reusable admin table: sorting, pagination, loading/error/empty states,
 * row actions, responsive horizontal scroll. Deliberately does NOT own
 * search/filter state — every existing manager page already has its own
 * search input + filter selects wired to local state, filtering `data`
 * before it ever reaches this component; DataTable just renders whatever
 * rows it's given. This keeps it a drop-in replacement for the existing
 * `<table>` markup in a manager page without requiring that page's
 * filter UI to be rebuilt.
 *
 * `columns`: [{ key, label, sortable, align, render(row), sortValue(row) }]
 * `render`/`sortValue` both default to `row[key]` when omitted. Put row
 * actions (edit/view buttons) in a plain non-sortable column like any
 * other — no separate prop for it, one column definition covers it.
 */
export default function DataTable({
  columns, data, loading, error, onRetry, emptyMessage = 'No records found.',
  getRowKey = row => row.id, minWidth = 700, pageSize = 10, onRowClick, header,
}) {
  const [sortKey, setSortKey] = useState(null)
  const [sortDir, setSortDir] = useState('asc')
  const [page, setPage] = useState(1)

  const sorted = useMemo(() => {
    if (!sortKey) return data
    const column = columns.find(c => c.key === sortKey)
    const accessor = column?.sortValue || (row => row[sortKey])
    const withValues = data.map((row, i) => ({ row, i, value: accessor(row) }))
    withValues.sort((a, b) => {
      const av = a.value, bv = b.value
      let cmp
      if (av == null && bv == null) cmp = 0
      else if (av == null) cmp = -1
      else if (bv == null) cmp = 1
      else if (typeof av === 'number' && typeof bv === 'number') cmp = av - bv
      else cmp = String(av).localeCompare(String(bv))
      if (cmp === 0) cmp = a.i - b.i // stable tiebreaker
      return sortDir === 'asc' ? cmp : -cmp
    })
    return withValues.map(w => w.row)
  }, [data, sortKey, sortDir, columns])

  const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize))
  // Clamp rather than reset-to-1 on every render: `data` is a fresh array
  // reference from the caller's own `.filter()` call on nearly every
  // render (including unrelated polling refreshes), not only when the
  // caller's actual search/filter criteria changed — resetting to page 1
  // every time would fight the user's own pagination navigation.
  useEffect(() => { setPage(p => Math.min(p, totalPages)) }, [totalPages])

  const pageRows = sorted.slice((page - 1) * pageSize, page * pageSize)

  function toggleSort(column) {
    if (!column.sortable) return
    if (sortKey !== column.key) { setSortKey(column.key); setSortDir('asc'); return }
    setSortDir(d => d === 'asc' ? 'desc' : 'asc')
  }

  if (loading) return <LoadingState label="records" />
  if (error) return <ErrorState message={error} onRetry={onRetry} />

  return <div className="card-k overflow-hidden">
    {header && <div className="flex flex-col gap-3 border-b border-kBorderSoft p-5 sm:flex-row">{header}</div>}
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm" style={{ minWidth }}>
        <thead className="bg-kBorderSoft text-xs uppercase tracking-wider text-kMuted">
          <tr>
            {columns.map(col => <th key={col.key} className={`px-5 py-4 ${col.align === 'right' ? 'text-right' : ''}`}>
              {col.sortable
                ? <button onClick={() => toggleSort(col)} className="inline-flex items-center gap-1 hover:text-kInk">
                    {col.label}
                    {sortKey === col.key ? (sortDir === 'asc' ? <ArrowUp size={12} /> : <ArrowDown size={12} />) : <ArrowUpDown size={12} className="opacity-40" />}
                  </button>
                : col.label}
            </th>)}
          </tr>
        </thead>
        <tbody>
          {pageRows.map(row => <tr
            key={getRowKey(row)}
            onClick={onRowClick ? () => onRowClick(row) : undefined}
            className={`border-b border-kBorderSoft last:border-0 ${onRowClick ? 'cursor-pointer hover:bg-kTint' : ''}`}
          >
            {columns.map(col => <td key={col.key} className={`px-5 py-4 ${col.align === 'right' ? 'text-right' : ''}`}>
              {col.render ? col.render(row) : row[col.key]}
            </td>)}
          </tr>)}
          {pageRows.length === 0 && <tr><td colSpan={columns.length} className="px-5 py-10 text-center text-sm text-kMuted">{emptyMessage}</td></tr>}
        </tbody>
      </table>
    </div>

    {sorted.length > 0 && totalPages > 1 && <div className="flex items-center justify-between border-t border-kBorderSoft px-5 py-3 text-sm text-kMuted">
      <span>Page {page} of {totalPages} &middot; {sorted.length} total</span>
      <div className="flex items-center gap-1">
        <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="grid h-8 w-8 place-items-center rounded-lg hover:bg-kTint disabled:cursor-not-allowed disabled:opacity-40"><ChevronLeft size={16} /></button>
        <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages} className="grid h-8 w-8 place-items-center rounded-lg hover:bg-kTint disabled:cursor-not-allowed disabled:opacity-40"><ChevronRight size={16} /></button>
      </div>
    </div>}
  </div>
}
