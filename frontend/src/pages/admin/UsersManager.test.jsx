import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import userEvent from '@testing-library/user-event'
import UsersManager from './UsersManager'
import { setSession, clearSession } from '../../lib/api'

vi.mock('../../components/admin/Shell', () => ({ default: ({ children }) => <div>{children}</div> }))

function jsonResponse(status, body) {
  return { status, ok: status >= 200 && status < 300, json: async () => body }
}

function renderPage() {
  return render(<MemoryRouter><UsersManager showToast={() => {}} /></MemoryRouter>)
}

const admin = { id: 1, name: 'Site Admin', email: 'admin@kdcce.org', role: 'admin' }

const staffUser = {
  id: 2, name: 'Jane Staffer', email: 'jane@kdcce.org', role: 'staff', active: true,
  last_login_at: '2026-08-30T10:00:00Z', two_factor_enabled: false, volunteer_status: null,
  deleted_at: null, created_at: '2026-01-01T00:00:00Z',
}

function setup(users) {
  localStorage.clear()
  setSession('t', admin, 'r')
  vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(jsonResponse(200, { users, pagination: { page: 1, per_page: 100, total: users.length, pages: 1 } }))))
}

describe('UsersManager', () => {
  afterEach(() => { vi.unstubAllGlobals(); clearSession() })

  it('shows a loading state, then renders the user table', async () => {
    setup([staffUser])
    renderPage()
    expect(screen.getByRole('status')).toBeInTheDocument()

    expect(await screen.findByText('Jane Staffer')).toBeInTheDocument()
    expect(screen.getByText('jane@kdcce.org')).toBeInTheDocument()
  })

  it('shows an empty state when there are no users', async () => {
    setup([])
    renderPage()
    expect(await screen.findByText(/no users match/i)).toBeInTheDocument()
  })

  it('shows an error state with a working retry button', async () => {
    localStorage.clear()
    setSession('t', admin, 'r')
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(jsonResponse(500, { error: 'Server exploded' }))
      .mockResolvedValueOnce(jsonResponse(200, { users: [staffUser], pagination: { page: 1, per_page: 100, total: 1, pages: 1 } }))
    vi.stubGlobal('fetch', fetchMock)

    renderPage()
    expect(await screen.findByText('Server exploded')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /try again/i }))
    expect(await screen.findByText('Jane Staffer')).toBeInTheDocument()
  })

  it('never exposes a password or password_hash field anywhere on the page', async () => {
    setup([staffUser])
    renderPage()
    await screen.findByText('Jane Staffer')
    expect(document.body.innerHTML).not.toMatch(/password_hash/i)
  })

  it('opens the create-user form and submits it', async () => {
    const fetchMock = vi.fn((url, opts) => {
      if (opts?.method === 'POST') return Promise.resolve(jsonResponse(201, { user: staffUser }))
      return Promise.resolve(jsonResponse(200, { users: [], pagination: { page: 1, per_page: 100, total: 0, pages: 0 } }))
    })
    localStorage.clear()
    setSession('t', admin, 'r')
    vi.stubGlobal('fetch', fetchMock)

    renderPage()
    await screen.findByText(/no users match/i)

    await userEvent.click(screen.getByRole('button', { name: /new user/i }))
    await userEvent.type(screen.getByLabelText(/^name$/i), 'New Person')
    await userEvent.type(screen.getByLabelText(/^email$/i), 'newperson@kdcce.org')
    await userEvent.type(screen.getByLabelText(/temporary password/i), 'hunter2222')
    await userEvent.click(screen.getByRole('button', { name: /create user/i }))

    await waitFor(() => {
      const postCall = fetchMock.mock.calls.find(c => c[1]?.method === 'POST')
      expect(postCall).toBeTruthy()
      expect(JSON.parse(postCall[1].body)).toMatchObject({ name: 'New Person', email: 'newperson@kdcce.org' })
    })
  })

  it('a staff viewer gets no user data on a 403 response', async () => {
    localStorage.clear()
    setSession('t', { id: 9, name: 'Staffer', role: 'staff' }, 'r')
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(jsonResponse(403, { error: 'Forbidden' }))))
    renderPage()
    expect(await screen.findByText('Forbidden')).toBeInTheDocument()
    expect(screen.queryByText('Jane Staffer')).not.toBeInTheDocument()
  })
})
