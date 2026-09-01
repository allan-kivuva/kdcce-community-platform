import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import userEvent from '@testing-library/user-event'
import CampaignsManager from './CampaignsManager'
import { setSession, clearSession } from '../../lib/api'

// Shell pulls in GlobalSearch/NotificationBell/QuickActionMenu, each with
// their own polling fetches unrelated to what this test covers — mocked
// out to a plain passthrough so this test only exercises CampaignsManager
// itself, same reasoning as mocking any other heavy, unrelated dependency.
vi.mock('../../components/admin/Shell', () => ({ default: ({ children }) => <div>{children}</div> }))

function jsonResponse(status, body) {
  return { status, ok: status >= 200 && status < 300, json: async () => body }
}

function renderPage() {
  return render(<MemoryRouter><CampaignsManager showToast={() => {}} /></MemoryRouter>)
}

const campaign = {
  id: 1, name: 'Feeding Drive', slug: null, description: 'Meals for elders', goal_amount: 1000,
  program_id: null, program_name: null, status: 'Active', public_visible: true,
  created_by: 'Admin', created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z',
  progress: { goal_amount: 1000, raised_amount: 650, remaining_amount: 350, percent_achieved: 65, donation_count: 12, recent_donations: [] },
}

describe('CampaignsManager', () => {
  afterEach(() => { vi.unstubAllGlobals(); clearSession() })

  function setup(campaigns) {
    localStorage.clear()
    setSession('t', { id: 1, name: 'Admin', role: 'admin' }, 'r')
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(jsonResponse(200, { campaigns }))))
  }

  it('shows a loading state, then renders campaign cards with progress', async () => {
    setup([campaign])
    renderPage()
    expect(screen.getByRole('status')).toBeInTheDocument()

    expect(await screen.findByText('Feeding Drive')).toBeInTheDocument()
    expect(screen.getByText('65%')).toBeInTheDocument()
    expect(screen.getByText('KES 650')).toBeInTheDocument()
  })

  it('shows an empty state when there are no campaigns', async () => {
    setup([])
    renderPage()
    expect(await screen.findByText(/no campaigns yet/i)).toBeInTheDocument()
  })

  it('shows an error state with a working retry button', async () => {
    localStorage.clear()
    setSession('t', { id: 1, name: 'Admin', role: 'admin' }, 'r')
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(jsonResponse(500, { error: 'Server exploded' }))
      .mockResolvedValueOnce(jsonResponse(200, { campaigns: [campaign] }))
    vi.stubGlobal('fetch', fetchMock)

    renderPage()
    expect(await screen.findByText('Server exploded')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /try again/i }))
    expect(await screen.findByText('Feeding Drive')).toBeInTheDocument()
  })

  it('opens the new-campaign form and submits it', async () => {
    const fetchMock = vi.fn((url, opts) => {
      if (opts?.method === 'POST') return Promise.resolve(jsonResponse(201, { campaign }))
      if (url.includes('/api/programs')) return Promise.resolve(jsonResponse(200, { programs: [] }))
      return Promise.resolve(jsonResponse(200, { campaigns: [] }))
    })
    localStorage.clear()
    setSession('t', { id: 1, name: 'Admin', role: 'admin' }, 'r')
    vi.stubGlobal('fetch', fetchMock)

    renderPage()
    await screen.findByText(/no campaigns yet/i)

    await userEvent.click(screen.getByRole('button', { name: /new campaign/i }))
    await userEvent.type(screen.getByLabelText(/^name$/i), 'Water Wells')
    await userEvent.type(screen.getByLabelText(/goal amount/i), '5000')
    await userEvent.click(screen.getByRole('button', { name: /create campaign/i }))

    await waitFor(() => {
      const postCall = fetchMock.mock.calls.find(c => c[1]?.method === 'POST')
      expect(postCall).toBeTruthy()
      expect(JSON.parse(postCall[1].body)).toMatchObject({ name: 'Water Wells', goal_amount: 5000 })
    })
  })

  it('a volunteer viewing this page sees no campaign data leak from a 403 response', async () => {
    localStorage.clear()
    setSession('t', { id: 1, name: 'Vol', role: 'volunteer' }, 'r')
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(jsonResponse(403, { error: 'Forbidden' }))))
    renderPage()
    expect(await screen.findByText('Forbidden')).toBeInTheDocument()
    expect(screen.queryByText('Feeding Drive')).not.toBeInTheDocument()
  })
})
