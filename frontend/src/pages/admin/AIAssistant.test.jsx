import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import userEvent from '@testing-library/user-event'
import AIAssistant from './AIAssistant'
import { setSession, clearSession } from '../../lib/api'

vi.mock('../../components/admin/Shell', () => ({ default: ({ children }) => <div>{children}</div> }))

function jsonResponse(status, body) {
  return { status, ok: status >= 200 && status < 300, json: async () => body }
}

function renderPage() {
  return render(<MemoryRouter><AIAssistant /></MemoryRouter>)
}

const emptyBriefing = {
  facts: {
    today: { visits_scheduled: 0, unassigned_requests: 0, high_priority_concerns_open: 0, unconfirmed_assignments: 0, events_today: [] },
    needs_attention: { members_without_recent_visits: [], stale_concerns: [], low_stock_items: [], understaffed_programs: [] },
    recent_activity: { visits_completed_yesterday: 0, achievements_awarded_yesterday: 0 },
  },
  briefing_text: 'GOOD MORNING\n\nTODAY\n- 0 home visit(s) scheduled',
  ai_used: false,
}

function mockEndpoints({ aiEnabled = false, queryResponse } = {}) {
  return vi.fn((url, opts) => {
    if (url.endsWith('/api/ai/admin/status')) return Promise.resolve(jsonResponse(200, { ai_enabled: aiEnabled }))
    if (url.endsWith('/api/ai/admin/briefing')) return Promise.resolve(jsonResponse(200, emptyBriefing))
    if (url.endsWith('/api/ai/admin/query') && opts?.method === 'POST') return Promise.resolve(jsonResponse(200, queryResponse))
    throw new Error('unexpected fetch: ' + url)
  })
}

describe('AIAssistant', () => {
  afterEach(() => { vi.unstubAllGlobals(); clearSession() })

  function setup(opts) {
    localStorage.clear()
    setSession('t', { id: 1, name: 'Admin', role: 'admin' }, 'r')
    vi.stubGlobal('fetch', mockEndpoints(opts))
  }

  it('shows the AI status badge and an empty state before any question is asked', async () => {
    setup({ aiEnabled: false })
    renderPage()
    expect(await screen.findByText('AI: Off')).toBeInTheDocument()
    expect(await screen.findByText(/ask anything about today's operations/i)).toBeInTheDocument()
    expect(screen.getByText('How many visits are scheduled today?')).toBeInTheDocument()
  })

  it('shows AI: On when the backend reports it enabled', async () => {
    setup({ aiEnabled: true })
    renderPage()
    expect(await screen.findByText('AI: On')).toBeInTheDocument()
  })

  it('renders the deterministic answer and a results table for a supported question', async () => {
    setup({
      queryResponse: {
        supported: true, intent: 'UNASSIGNED_REQUESTS', answer: '2 assistance request(s) are currently unassigned.',
        ai_explanation: '2 assistance request(s) are currently unassigned.', ai_used: false,
        results: [
          { id: 1, member_name: 'Mary W', request_type: 'Transportation', priority: 'Medium', status: 'Requested' },
          { id: 2, member_name: 'John O', request_type: 'Shopping', priority: 'Low', status: 'Requested' },
        ],
      },
    })
    renderPage()
    await userEvent.type(screen.getByPlaceholderText(/ask about visits/i), 'Show unassigned assistance requests.')
    await userEvent.click(screen.getByRole('button', { name: /^ask$/i }))

    expect(await screen.findByText('2 assistance request(s) are currently unassigned.')).toBeInTheDocument()
    expect(await screen.findByText('Mary W')).toBeInTheDocument()
    expect(screen.getByText('John O')).toBeInTheDocument()
  })

  it('clicking a suggested prompt asks it directly', async () => {
    const fetchMock = mockEndpoints({
      queryResponse: { supported: true, intent: 'VISITS_TODAY', answer: 'No home visits are scheduled today.', ai_explanation: 'No home visits are scheduled today.', ai_used: false, results: [] },
    })
    localStorage.clear()
    setSession('t', { id: 1, name: 'Admin', role: 'admin' }, 'r')
    vi.stubGlobal('fetch', fetchMock)

    renderPage()
    await userEvent.click(await screen.findByText('How many visits are scheduled today?'))

    await waitFor(() => {
      const call = fetchMock.mock.calls.find(c => c[0].endsWith('/api/ai/admin/query'))
      expect(call).toBeTruthy()
      expect(JSON.parse(call[1].body)).toEqual({ question: 'How many visits are scheduled today?' })
    })
    expect(await screen.findByText('No home visits are scheduled today.')).toBeInTheDocument()
  })

  it('shows the unsupported-question fallback with example prompts', async () => {
    setup({
      queryResponse: { supported: false, message: "I don't have a way to answer that yet. Try one of the supported questions below.", examples: ['How many visits are scheduled today?'] },
    })
    renderPage()
    await userEvent.type(screen.getByPlaceholderText(/ask about visits/i), 'What is the meaning of life?')
    await userEvent.click(screen.getByRole('button', { name: /^ask$/i }))

    expect(await screen.findByText(/don't have a way to answer that yet/i)).toBeInTheDocument()
  })

  it('shows an error state with a working retry on a failed query', async () => {
    localStorage.clear()
    setSession('t', { id: 1, name: 'Admin', role: 'admin' }, 'r')
    const fetchMock = vi.fn((url, opts) => {
      if (url.endsWith('/api/ai/admin/status')) return Promise.resolve(jsonResponse(200, { ai_enabled: false }))
      if (url.endsWith('/api/ai/admin/briefing')) return Promise.resolve(jsonResponse(200, emptyBriefing))
      if (url.endsWith('/api/ai/admin/query')) return Promise.resolve(jsonResponse(500, { error: 'Server exploded' }))
      throw new Error('unexpected fetch: ' + url)
    })
    vi.stubGlobal('fetch', fetchMock)

    renderPage()
    await userEvent.type(screen.getByPlaceholderText(/ask about visits/i), 'How many visits are scheduled today?')
    await userEvent.click(screen.getByRole('button', { name: /^ask$/i }))

    expect(await screen.findByText('Server exploded')).toBeInTheDocument()
  })

  it('renders the daily briefing stat tiles from real facts', async () => {
    localStorage.clear()
    setSession('t', { id: 1, name: 'Admin', role: 'admin' }, 'r')
    vi.stubGlobal('fetch', vi.fn((url) => {
      if (url.endsWith('/api/ai/admin/status')) return Promise.resolve(jsonResponse(200, { ai_enabled: false }))
      if (url.endsWith('/api/ai/admin/briefing')) return Promise.resolve(jsonResponse(200, {
        ...emptyBriefing,
        facts: { ...emptyBriefing.facts, today: { ...emptyBriefing.facts.today, visits_scheduled: 3, unassigned_requests: 1 } },
      }))
      throw new Error('unexpected fetch: ' + url)
    }))

    renderPage()
    expect(await screen.findByText('3')).toBeInTheDocument()
    expect(screen.getByText('Visits scheduled')).toBeInTheDocument()
  })

  it('a 403 from the API surfaces as an error, never a silent blank page', async () => {
    localStorage.clear()
    setSession('t', { id: 9, name: 'Staffer', role: 'staff' }, 'r')
    vi.stubGlobal('fetch', vi.fn((url) => {
      if (url.endsWith('/api/ai/admin/status')) return Promise.resolve(jsonResponse(403, { error: 'Forbidden' }))
      if (url.endsWith('/api/ai/admin/briefing')) return Promise.resolve(jsonResponse(403, { error: 'Forbidden' }))
      throw new Error('unexpected fetch: ' + url)
    }))
    renderPage()
    expect(await screen.findByText('Forbidden')).toBeInTheDocument()
  })
})
