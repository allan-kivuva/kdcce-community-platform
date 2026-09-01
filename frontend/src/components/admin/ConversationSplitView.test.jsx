import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ConversationSplitView from './ConversationSplitView'

function items(n) {
  return Array.from({ length: n }, (_, i) => ({
    key: `k${i}`, icon: <span>icon</span>, title: `Person ${i + 1}`, subtitle: 'volunteer',
    preview: `Last message ${i + 1}`, timestamp: '2h ago', unread: i === 0, badge: i === 0 ? 3 : 0,
  }))
}

const noop = () => {}
const search = { value: '', onChange: noop }

describe('ConversationSplitView', () => {
  it('shows a loading state and nothing else while loading', () => {
    render(<ConversationSplitView items={[]} selectedKey={null} onSelect={noop} loading error="" onRetry={noop} search={search} />)
    expect(screen.getByRole('status')).toBeInTheDocument()
  })

  it('shows an error state with a working retry button', async () => {
    const onRetry = vi.fn()
    render(<ConversationSplitView items={[]} selectedKey={null} onSelect={noop} loading={false} error="Broke" onRetry={onRetry} search={search} />)
    expect(screen.getByText('Broke')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /try again/i }))
    expect(onRetry).toHaveBeenCalledOnce()
  })

  it('shows the empty message when there are no conversations', () => {
    render(<ConversationSplitView items={[]} selectedKey={null} onSelect={noop} loading={false} error="" onRetry={noop} search={search} emptyMessage="Nothing here." />)
    expect(screen.getByText('Nothing here.')).toBeInTheDocument()
  })

  it('renders one entry per conversation with title, preview, and an unread badge', () => {
    render(<ConversationSplitView items={items(2)} selectedKey={null} onSelect={noop} loading={false} error="" onRetry={noop} search={search} />)
    expect(screen.getByText('Person 1')).toBeInTheDocument()
    expect(screen.getByText('Person 2')).toBeInTheDocument()
    expect(screen.getByText('Last message 1')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument() // unread badge on the first item only
  })

  it('calls onSelect with the item key when a conversation is clicked', async () => {
    const onSelect = vi.fn()
    render(<ConversationSplitView items={items(2)} selectedKey={null} onSelect={onSelect} loading={false} error="" onRetry={noop} search={search} />)
    await userEvent.click(screen.getByText('Person 2'))
    expect(onSelect).toHaveBeenCalledWith('k1')
  })

  it('shows a placeholder in the thread pane when nothing is selected', () => {
    render(<ConversationSplitView items={items(1)} selectedKey={null} onSelect={noop} loading={false} error="" onRetry={noop} search={search}>
      <div>Thread content</div>
    </ConversationSplitView>)
    expect(screen.getByText(/select a conversation/i)).toBeInTheDocument()
    expect(screen.queryByText('Thread content')).not.toBeInTheDocument()
  })

  it('renders the thread pane and a mobile back button once a conversation is selected', async () => {
    const onSelect = vi.fn()
    render(<ConversationSplitView items={items(1)} selectedKey="k0" onSelect={onSelect} loading={false} error="" onRetry={noop} search={search}>
      <div>Thread content</div>
    </ConversationSplitView>)
    expect(screen.getByText('Thread content')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /back to conversations/i }))
    expect(onSelect).toHaveBeenCalledWith(null)
  })

  it('keeps the open thread visible during a background list refresh (loading=true with a selection)', () => {
    // Regression test: a background reload (e.g. after sending a reply,
    // which re-triggers `loading`) must never unmount the open thread —
    // that previously caused a mount-effect loop (mark-read -> reload ->
    // thread unmounts -> remounts -> mark-read -> ...).
    render(<ConversationSplitView items={items(1)} selectedKey="k0" onSelect={noop} loading error="" onRetry={noop} search={search}>
      <div>Thread content</div>
    </ConversationSplitView>)
    expect(screen.getByText('Thread content')).toBeInTheDocument()
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('propagates search input changes via search.onChange', async () => {
    const onChange = vi.fn()
    render(<ConversationSplitView items={items(1)} selectedKey={null} onSelect={noop} loading={false} error="" onRetry={noop} search={{ value: '', onChange }} />)
    await userEvent.type(screen.getByPlaceholderText('Search...'), 'a')
    expect(onChange).toHaveBeenCalledWith('a')
  })

  it('renders custom header actions next to the search box', () => {
    render(<ConversationSplitView items={[]} selectedKey={null} onSelect={noop} loading={false} error="" onRetry={noop} search={search} headerActions={<button>New</button>} />)
    expect(screen.getByRole('button', { name: 'New' })).toBeInTheDocument()
  })
})
