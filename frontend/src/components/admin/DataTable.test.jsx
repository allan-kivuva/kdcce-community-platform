import { describe, it, expect, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import DataTable from './DataTable'

const columns = [
  { key: 'name', label: 'Name', sortable: true },
  { key: 'age', label: 'Age', sortable: true },
]

function rows(n) {
  return Array.from({ length: n }, (_, i) => ({ id: i + 1, name: `Person ${i + 1}`, age: n - i }))
}

function bodyRows() {
  return within(screen.getByRole('table')).getAllByRole('row').slice(1) // drop header row
}

describe('DataTable', () => {
  it('shows a loading state and no table while loading', () => {
    render(<DataTable columns={columns} data={[]} loading />)
    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('shows an error state with a retry button, not the table', async () => {
    const onRetry = vi.fn()
    render(<DataTable columns={columns} data={[]} error="Something broke" onRetry={onRetry} />)
    expect(screen.getByText('Something broke')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /try again/i }))
    expect(onRetry).toHaveBeenCalledOnce()
  })

  it('shows the empty message when data is empty', () => {
    render(<DataTable columns={columns} data={[]} emptyMessage="Nothing here yet." />)
    expect(screen.getByText('Nothing here yet.')).toBeInTheDocument()
  })

  it('renders one row per data item with the right cell values', () => {
    render(<DataTable columns={columns} data={rows(3)} />)
    const trs = bodyRows()
    expect(trs).toHaveLength(3)
    expect(within(trs[0]).getByText('Person 1')).toBeInTheDocument()
    expect(within(trs[0]).getByText('3')).toBeInTheDocument() // age = 3 - 0
  })

  it('sorts ascending then descending on repeated header clicks', async () => {
    render(<DataTable columns={columns} data={rows(3)} />) // ages: 3, 2, 1 (unsorted)
    const nameHeader = screen.getByRole('button', { name: /name/i })

    await userEvent.click(nameHeader) // ascending by name
    let names = bodyRows().map(tr => within(tr).getAllByRole('cell')[0].textContent)
    expect(names).toEqual(['Person 1', 'Person 2', 'Person 3'])

    await userEvent.click(nameHeader) // descending
    names = bodyRows().map(tr => within(tr).getAllByRole('cell')[0].textContent)
    expect(names).toEqual(['Person 3', 'Person 2', 'Person 1'])
  })

  it('sorts numerically, not lexically, for a numeric column', async () => {
    const data = [{ id: 1, name: 'A', age: 9 }, { id: 2, name: 'B', age: 10 }, { id: 3, name: 'C', age: 2 }]
    render(<DataTable columns={columns} data={data} />)
    await userEvent.click(screen.getByRole('button', { name: /age/i }))
    const ages = bodyRows().map(tr => within(tr).getAllByRole('cell')[1].textContent)
    expect(ages).toEqual(['2', '9', '10']) // not the lexical '10','2','9'
  })

  it('uses a custom sortValue accessor when given', async () => {
    const rank = { Low: 0, High: 1 }
    const cols = [{ key: 'priority', label: 'Priority', sortable: true, sortValue: r => rank[r.priority] }]
    const data = [{ id: 1, priority: 'High' }, { id: 2, priority: 'Low' }]
    render(<DataTable columns={cols} data={data} />)
    await userEvent.click(screen.getByRole('button', { name: /priority/i }))
    const values = bodyRows().map(tr => within(tr).getAllByRole('cell')[0].textContent)
    expect(values).toEqual(['Low', 'High'])
  })

  it('does not sort on a non-sortable column header (plain text, not a button)', () => {
    const cols = [{ key: 'name', label: 'Name' }] // sortable omitted
    render(<DataTable columns={cols} data={rows(2)} />)
    expect(screen.queryByRole('button', { name: /name/i })).not.toBeInTheDocument()
  })

  it('paginates: shows only pageSize rows per page and navigates with next/prev', async () => {
    render(<DataTable columns={columns} data={rows(25)} pageSize={10} />)
    expect(bodyRows()).toHaveLength(10)
    expect(screen.getByText('Page 1 of 3 · 25 total')).toBeInTheDocument()

    const [prevBtn, nextBtn] = screen.getAllByRole('button').filter(b => !b.textContent.trim())
    expect(prevBtn).toBeDisabled()

    await userEvent.click(nextBtn)
    expect(screen.getByText('Page 2 of 3 · 25 total')).toBeInTheDocument()
    expect(bodyRows()).toHaveLength(10)

    await userEvent.click(nextBtn)
    expect(screen.getByText('Page 3 of 3 · 25 total')).toBeInTheDocument()
    expect(bodyRows()).toHaveLength(5) // remainder
    expect(nextBtn).toBeDisabled()
  })

  it('hides pagination controls entirely when everything fits on one page', () => {
    render(<DataTable columns={columns} data={rows(5)} pageSize={10} />)
    expect(screen.queryByText(/Page \d+ of \d+/)).not.toBeInTheDocument()
  })

  it('clamps the current page down when the data set shrinks below it', async () => {
    const { rerender } = render(<DataTable columns={columns} data={rows(25)} pageSize={10} />)
    const nextBtn = screen.getAllByRole('button').filter(b => !b.textContent.trim())[1]
    await userEvent.click(nextBtn)
    await userEvent.click(nextBtn)
    expect(screen.getByText('Page 3 of 3 · 25 total')).toBeInTheDocument()

    rerender(<DataTable columns={columns} data={rows(3)} pageSize={10} />) // now only 1 page's worth
    expect(screen.queryByText(/Page \d+ of \d+/)).not.toBeInTheDocument()
    expect(bodyRows()).toHaveLength(3)
  })

  it('calls onRowClick with the row when a row is clicked, and not otherwise', async () => {
    const onRowClick = vi.fn()
    render(<DataTable columns={columns} data={rows(2)} onRowClick={onRowClick} />)
    await userEvent.click(bodyRows()[0])
    expect(onRowClick).toHaveBeenCalledWith(expect.objectContaining({ name: 'Person 1' }))
  })

  it('renders the header slot above the table when given', () => {
    render(<DataTable columns={columns} data={rows(1)} header={<input placeholder="Search..." />} />)
    expect(screen.getByPlaceholderText('Search...')).toBeInTheDocument()
  })
})
