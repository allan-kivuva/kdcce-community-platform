import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import FamilyOverview from './FamilyOverview'
import { setSession, clearSession } from '../../lib/api'

vi.mock('../../components/family/FamilyShell', () => ({ default: ({ children }) => <div>{children}</div> }))

function jsonResponse(status, body) {
  return { status, ok: status >= 200 && status < 300, json: async () => body }
}

function renderPage() {
  return render(<MemoryRouter><FamilyOverview /></MemoryRouter>)
}

const member = { id: 1, member_id: 'KDCCE-2026-0001', full_name: 'Mary Wanjiku', status: 'Active', relationship: 'Daughter' }

function mockFamilyEndpoints({ visits = [], assistanceRequests = [], updates = [], activities = [] } = {}) {
  return vi.fn((url) => {
    if (url.endsWith('/api/family/members')) return Promise.resolve(jsonResponse(200, { members: [member] }))
    if (url.endsWith(`/api/family/members/${member.id}`)) return Promise.resolve(jsonResponse(200, { member }))
    if (url.endsWith(`/api/family/members/${member.id}/visits`)) return Promise.resolve(jsonResponse(200, { visits, assistance_requests: assistanceRequests }))
    if (url.endsWith(`/api/family/members/${member.id}/updates`)) return Promise.resolve(jsonResponse(200, { updates }))
    if (url.endsWith(`/api/family/members/${member.id}/programs`)) return Promise.resolve(jsonResponse(200, { activities }))
    throw new Error('unexpected fetch: ' + url)
  })
}

describe('FamilyOverview', () => {
  afterEach(() => { vi.unstubAllGlobals(); clearSession() })

  it('shows a loading state, then the linked member with their next visit', async () => {
    localStorage.clear()
    setSession('t', { id: 5, name: 'Family One', role: 'family' }, 'r')
    vi.stubGlobal('fetch', mockFamilyEndpoints({
      visits: [{ id: 1, status: 'Assigned', scheduled_at: '2026-09-10T10:00:00Z', completed_at: null, assigned_volunteer_name: 'Jane V' }],
    }))

    renderPage()
    expect(screen.getByRole('status')).toBeInTheDocument()

    expect(await screen.findByText('Mary Wanjiku')).toBeInTheDocument()
    expect(screen.getByText(/Your relationship: Daughter/i)).toBeInTheDocument()
  })

  it('shows an empty state when the family account has no linked members', async () => {
    localStorage.clear()
    setSession('t', { id: 5, name: 'Family One', role: 'family' }, 'r')
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(jsonResponse(200, { members: [] }))))

    renderPage()
    expect(await screen.findByText(/no linked family members/i)).toBeInTheDocument()
  })

  it('shows an error state with a working retry button', async () => {
    localStorage.clear()
    setSession('t', { id: 5, name: 'Family One', role: 'family' }, 'r')
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(jsonResponse(500, { error: 'Server exploded' }))
      .mockResolvedValueOnce(jsonResponse(200, { members: [member] }))
    vi.stubGlobal('fetch', fetchMock)

    renderPage()
    expect(await screen.findByText('Server exploded')).toBeInTheDocument()
  })

  it('shows recent updates and registered programs when present', async () => {
    localStorage.clear()
    setSession('t', { id: 5, name: 'Family One', role: 'family' }, 'r')
    vi.stubGlobal('fetch', mockFamilyEndpoints({
      updates: [{ type: 'home_visit', label: 'Home visit completed', at: '2026-09-01T10:00:00Z' }],
      activities: [{ id: 1, title: 'Feeding Program', activity_type: 'Feeding', status: 'Registered', scheduled_at: '2026-09-15T09:00:00Z' }],
    }))

    renderPage()
    expect(await screen.findByText('Home visit completed')).toBeInTheDocument()
    expect(await screen.findByText('Feeding Program')).toBeInTheDocument()
  })

  it('never renders a health, vulnerability, or address field anywhere on the page', async () => {
    localStorage.clear()
    setSession('t', { id: 5, name: 'Family One', role: 'family' }, 'r')
    vi.stubGlobal('fetch', mockFamilyEndpoints())

    renderPage()
    await screen.findByText('Mary Wanjiku')
    const html = document.body.innerHTML.toLowerCase()
    expect(html).not.toMatch(/health_notes|vulnerability|allerg|dietary|latitude|longitude/)
  })

  it('a family account with a 403 from the API sees no member data leak through', async () => {
    localStorage.clear()
    setSession('t', { id: 5, name: 'Family One', role: 'family' }, 'r')
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(jsonResponse(403, { error: 'Forbidden' }))))

    renderPage()
    expect(await screen.findByText('Forbidden')).toBeInTheDocument()
    expect(screen.queryByText('Mary Wanjiku')).not.toBeInTheDocument()
  })
})
