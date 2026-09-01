import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import DirectConversationThread from './DirectConversationThread'
import { setSession, clearSession } from '../../lib/api'

function jsonResponse(status, body) {
  return { status, ok: status >= 200 && status < 300, json: async () => body }
}

const otherUser = { name: 'Staff Person', role: 'staff' }
const conversationDetail = {
  conversation: {
    id: 1,
    other_user: { id: 2, name: 'Staff Person', role: 'staff' },
    messages: [
      { id: 1, sender_id: 2, sender_name: 'Staff Person', body: 'Hello there', created_at: '2026-01-01T10:00:00Z' },
      { id: 2, sender_id: 1, sender_name: 'Me', body: 'Hi back', created_at: '2026-01-01T10:05:00Z' },
    ],
  },
}

describe('DirectConversationThread', () => {
  beforeEach(() => {
    localStorage.clear()
    setSession('token', { id: 1, name: 'Me', role: 'volunteer' }, 'refresh')
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    clearSession()
  })

  it('loads and renders message history, distinguishing my own messages', async () => {
    fetch
      .mockResolvedValueOnce(jsonResponse(200, conversationDetail)) // GET conversation
      .mockResolvedValueOnce(jsonResponse(200, { conversation: conversationDetail.conversation })) // PATCH read

    render(<DirectConversationThread conversationId={1} otherUser={otherUser} />)

    expect(await screen.findByText('Hello there')).toBeInTheDocument()
    expect(screen.getByText('Hi back')).toBeInTheDocument()
    expect(screen.getAllByText('Staff Person').length).toBeGreaterThan(0)
  })

  it('marks the conversation read on open', async () => {
    fetch
      .mockResolvedValueOnce(jsonResponse(200, conversationDetail))
      .mockResolvedValueOnce(jsonResponse(200, { conversation: conversationDetail.conversation }))
    const onRead = vi.fn()

    render(<DirectConversationThread conversationId={1} otherUser={otherUser} onRead={onRead} />)

    await waitFor(() => expect(onRead).toHaveBeenCalled())
    const readCall = fetch.mock.calls.find(c => c[0].includes('/read'))
    expect(readCall[1].method).toBe('PATCH')
  })

  it('sends a reply and reloads the thread', async () => {
    fetch
      .mockResolvedValueOnce(jsonResponse(200, conversationDetail)) // initial GET
      .mockResolvedValueOnce(jsonResponse(200, { conversation: conversationDetail.conversation })) // PATCH read
      .mockResolvedValueOnce(jsonResponse(201, { message: { id: 3, sender_id: 1, sender_name: 'Me', body: 'New reply', created_at: '2026-01-01T10:10:00Z' } })) // POST message
      .mockResolvedValueOnce(jsonResponse(200, { // reload after send
        conversation: { ...conversationDetail.conversation, messages: [...conversationDetail.conversation.messages, { id: 3, sender_id: 1, sender_name: 'Me', body: 'New reply', created_at: '2026-01-01T10:10:00Z' }] },
      }))

    render(<DirectConversationThread conversationId={1} otherUser={otherUser} />)
    await screen.findByText('Hello there')

    await userEvent.type(screen.getByPlaceholderText(/write a message/i), 'New reply')
    await userEvent.click(screen.getByRole('button', { name: '' })) // send icon button, no accessible text

    await waitFor(() => expect(screen.getByText('New reply')).toBeInTheDocument())
    const sendCall = fetch.mock.calls.find(c => c[1]?.method === 'POST')
    expect(JSON.parse(sendCall[1].body)).toEqual({ body: 'New reply' })
  })

  it('notifies the parent (onRead) after sending, not just on open — so a stale Needs-Reply badge refreshes', async () => {
    fetch
      .mockResolvedValueOnce(jsonResponse(200, conversationDetail))
      .mockResolvedValueOnce(jsonResponse(200, { conversation: conversationDetail.conversation })) // PATCH read on open
      .mockResolvedValueOnce(jsonResponse(201, { message: { id: 3, sender_id: 1, sender_name: 'Me', body: 'New reply', created_at: '2026-01-01T10:10:00Z' } }))
      .mockResolvedValueOnce(jsonResponse(200, { conversation: conversationDetail.conversation }))
    const onRead = vi.fn()

    render(<DirectConversationThread conversationId={1} otherUser={otherUser} onRead={onRead} />)
    await screen.findByText('Hello there')
    await waitFor(() => expect(onRead).toHaveBeenCalledTimes(1)) // the mark-read-on-open call

    await userEvent.type(screen.getByPlaceholderText(/write a message/i), 'New reply')
    await userEvent.click(screen.getAllByRole('button').find(b => b.disabled === false))

    await waitFor(() => expect(onRead).toHaveBeenCalledTimes(2)) // again after sending
  })

  it('does not allow sending an empty message', async () => {
    fetch
      .mockResolvedValueOnce(jsonResponse(200, conversationDetail))
      .mockResolvedValueOnce(jsonResponse(200, { conversation: conversationDetail.conversation }))

    render(<DirectConversationThread conversationId={1} otherUser={otherUser} />)
    await screen.findByText('Hello there')

    const sendButton = screen.getAllByRole('button').find(b => b.disabled !== undefined && !b.textContent.trim())
    expect(sendButton).toBeDisabled()
  })
})
