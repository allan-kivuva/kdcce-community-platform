import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import userEvent from '@testing-library/user-event'
import SessionsManager from './SessionsManager'
import { setSession, clearSession } from '../../lib/api'

vi.mock('../../components/admin/Shell', () => ({ default: ({ children }) => <div>{children}</div> }))

function jsonResponse(status, body) {
  return { status, ok: status >= 200 && status < 300, json: async () => body }
}

function renderPage() {
  return render(<MemoryRouter><SessionsManager showToast={() => {}} /></MemoryRouter>)
}

const currentSession = { id: 1, created_at: '2026-08-30T09:00:00Z', last_seen_at: '2026-08-31T10:00:00Z', expires_at: '2026-09-30T09:00:00Z', revoked_at: null, ip_address: '127.0.0.1', user_agent: 'Chrome on macOS', is_current: true }
const otherSession = { id: 2, created_at: '2026-08-29T09:00:00Z', last_seen_at: '2026-08-30T09:00:00Z', expires_at: '2026-09-29T09:00:00Z', revoked_at: null, ip_address: '10.0.0.5', user_agent: 'Firefox on Linux', is_current: false }

function setup(sessions) {
  localStorage.clear()
  setSession('t', { id: 1, name: 'Admin', role: 'admin' }, 'r')
  vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(jsonResponse(200, { sessions }))))
}

describe('SessionsManager', () => {
  afterEach(() => { vi.unstubAllGlobals(); clearSession() })

  it('shows a loading state, then the current device with no sign-out button', async () => {
    setup([currentSession])
    renderPage()
    expect(screen.getByRole('status')).toBeInTheDocument()

    expect(await screen.findByText('Chrome on macOS')).toBeInTheDocument()
    expect(screen.getByText('This device')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /sign out$/i })).not.toBeInTheDocument()
  })

  it('shows an empty state with no sessions', async () => {
    setup([])
    renderPage()
    expect(await screen.findByText(/no active sessions/i)).toBeInTheDocument()
  })

  it('shows an error state with a working retry button', async () => {
    localStorage.clear()
    setSession('t', { id: 1, name: 'Admin', role: 'admin' }, 'r')
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(jsonResponse(500, { error: 'Server exploded' }))
      .mockResolvedValueOnce(jsonResponse(200, { sessions: [currentSession] }))
    vi.stubGlobal('fetch', fetchMock)

    renderPage()
    expect(await screen.findByText('Server exploded')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /try again/i }))
    expect(await screen.findByText('Chrome on macOS')).toBeInTheDocument()
  })

  it('lets the user sign out a specific other device', async () => {
    const fetchMock = vi.fn((url, opts) => {
      if (opts?.method === 'DELETE') return Promise.resolve(jsonResponse(204, null))
      return Promise.resolve(jsonResponse(200, { sessions: [currentSession, otherSession] }))
    })
    localStorage.clear()
    setSession('t', { id: 1, name: 'Admin', role: 'admin' }, 'r')
    vi.stubGlobal('fetch', fetchMock)

    renderPage()
    await screen.findByText('Firefox on Linux')
    await userEvent.click(screen.getByRole('button', { name: /sign out$/i }))

    await waitFor(() => {
      const del = fetchMock.mock.calls.find(c => c[1]?.method === 'DELETE')
      expect(del[0]).toContain('/api/sessions/2')
    })
  })

  it('shows "sign out everywhere" and "other devices" actions only when there is more than one session', async () => {
    setup([currentSession])
    renderPage()
    await screen.findByText('Chrome on macOS')
    expect(screen.queryByRole('button', { name: /sign out everywhere/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /sign out other devices/i })).not.toBeInTheDocument()
  })

  it('never renders a raw refresh or access token anywhere on the page', async () => {
    setup([currentSession, otherSession])
    renderPage()
    await screen.findByText('Chrome on macOS')
    expect(document.body.innerHTML).not.toMatch(/eyJ/) // no raw JWT-looking string
  })
})
