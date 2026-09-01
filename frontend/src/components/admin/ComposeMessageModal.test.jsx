import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ComposeMessageModal from './ComposeMessageModal'
import { setSession, clearSession } from '../../lib/api'

function jsonResponse(status, body) {
  return { status, ok: status >= 200 && status < 300, json: async () => body }
}

const recipients = { recipients: [{ id: 5, name: 'Staff Member', role: 'staff' }] }
const templates = { templates: [{ key: 'general_check_in', title: 'General Check-in', body: 'Hi {name}, just checking in.' }] }

describe('ComposeMessageModal', () => {
  afterEach(() => { vi.unstubAllGlobals(); clearSession() })

  it('a volunteer sees recipients but not a template picker', async () => {
    localStorage.clear()
    setSession('t', { id: 1, name: 'Me', role: 'volunteer' }, 'r')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(200, recipients)))

    render(<ComposeMessageModal onClose={() => {}} showToast={() => {}} />)
    expect(await screen.findByText('Staff Member (staff)')).toBeInTheDocument()
    expect(screen.queryByText(/template/i)).not.toBeInTheDocument()
  })

  it('admin/staff sees a template picker that populates the message body', async () => {
    localStorage.clear()
    setSession('t', { id: 5, name: 'Admin', role: 'admin' }, 'r')
    vi.stubGlobal('fetch', vi.fn((url) => url.includes('/templates') ? Promise.resolve(jsonResponse(200, templates)) : Promise.resolve(jsonResponse(200, recipients))))

    render(<ComposeMessageModal onClose={() => {}} showToast={() => {}} />)
    await screen.findByText('Staff Member (staff)')

    await userEvent.selectOptions(screen.getByRole('combobox', { name: /to/i }), '5')
    await userEvent.selectOptions(screen.getByRole('combobox', { name: /template/i }), 'general_check_in')

    expect(screen.getByPlaceholderText(/write your message/i)).toHaveValue('Hi Staff, just checking in.')
  })

  it('sends the message with the chosen recipient and body', async () => {
    localStorage.clear()
    setSession('t', { id: 1, name: 'Me', role: 'volunteer' }, 'r')
    const fetchMock = vi.fn((url) => {
      if (url.includes('/recipients')) return Promise.resolve(jsonResponse(200, recipients))
      return Promise.resolve(jsonResponse(201, { conversation: { id: 1 } }))
    })
    vi.stubGlobal('fetch', fetchMock)
    const onSent = vi.fn()

    render(<ComposeMessageModal onClose={() => {}} onSent={onSent} showToast={() => {}} />)
    await screen.findByText('Staff Member (staff)')

    await userEvent.selectOptions(screen.getByRole('combobox', { name: /to/i }), '5')
    await userEvent.type(screen.getByPlaceholderText(/write your message/i), 'Hello!')
    await userEvent.click(screen.getByRole('button', { name: /send message/i }))

    const sendCall = fetchMock.mock.calls.find(c => c[1]?.method === 'POST')
    expect(JSON.parse(sendCall[1].body)).toEqual({ recipient_id: 5, body: 'Hello!' })
    expect(onSent).toHaveBeenCalled()
  })
})
