import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import userEvent from '@testing-library/user-event'
import VolunteerPrograms from './VolunteerPrograms'
import { setSession, clearSession } from '../../lib/api'
import { ThemeProvider } from '../../theme/ThemeProvider'

function renderPage(props) {
  return render(<MemoryRouter><ThemeProvider><VolunteerPrograms {...props} /></ThemeProvider></MemoryRouter>)
}

function jsonResponse(status, body) {
  return { status, ok: status >= 200 && status < 300, json: async () => body }
}

const futureActivity = {
  id: 1, title: 'Community Fair', activity_type: 'Community Event', status: 'Scheduled',
  scheduled_at: '2099-01-15T09:00:00+00:00', location: 'Community Hall', description: 'A fun fair.',
  program_id: null, program_name: null, capacity: 2, registration_open: true, registration_deadline: null,
  confirmed_volunteer_count: 1, spots_remaining: 1, waitlist_count: 0, participant_count: 0,
}
const pastActivity = { ...futureActivity, id: 2, title: 'Old Event', scheduled_at: '2020-01-15T09:00:00+00:00' }

function mockFetchRouter(routes) {
  return vi.fn((url, opts = {}) => {
    for (const [matcher, handler] of routes) {
      if (typeof matcher === 'string' ? url.includes(matcher) : matcher.test(url)) {
        return Promise.resolve(handler(url, opts))
      }
    }
    return Promise.resolve(jsonResponse(404, { error: 'not found' }))
  })
}

describe('VolunteerPrograms', () => {
  afterEach(() => { vi.unstubAllGlobals(); clearSession() })

  function setup(routes) {
    localStorage.clear()
    setSession('t', { id: 1, name: 'Me', role: 'volunteer' }, 'r')
    vi.stubGlobal('fetch', mockFetchRouter(routes))
  }

  it('shows a loading state, then upcoming activities by default', async () => {
    setup([
      ['/api/activities/me/assignments', () => jsonResponse(200, { assignments: [] })],
      ['/api/activities', () => jsonResponse(200, { activities: [futureActivity, pastActivity] })],
    ])
    renderPage({ showToast: () => {} })
    expect(screen.getByRole('status')).toBeInTheDocument()

    expect(await screen.findByText('Community Fair')).toBeInTheDocument()
    expect(screen.queryByText('Old Event')).not.toBeInTheDocument() // upcoming filter excludes past
  })

  it('shows an empty state when nothing matches the filter', async () => {
    setup([
      ['/api/activities/me/assignments', () => jsonResponse(200, { assignments: [] })],
      ['/api/activities', () => jsonResponse(200, { activities: [] })],
    ])
    renderPage({ showToast: () => {} })
    expect(await screen.findByText(/nothing here/i)).toBeInTheDocument()
  })

  it('shows an error state with retry on a failed fetch', async () => {
    setup([
      ['/api/activities/me/assignments', () => jsonResponse(200, { assignments: [] })],
      ['/api/activities', () => jsonResponse(500, { error: 'Server exploded' })],
    ])
    renderPage({ showToast: () => {} })
    expect(await screen.findByText('Server exploded')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument()
  })

  it('switching to Past shows past activities and hides upcoming ones', async () => {
    setup([
      ['/api/activities/me/assignments', () => jsonResponse(200, { assignments: [] })],
      ['/api/activities', () => jsonResponse(200, { activities: [futureActivity, pastActivity] })],
    ])
    renderPage({ showToast: () => {} })
    await screen.findByText('Community Fair')

    await userEvent.click(screen.getByRole('button', { name: 'Past' }))
    expect(screen.getByText('Old Event')).toBeInTheDocument()
    expect(screen.queryByText('Community Fair')).not.toBeInTheDocument()
  })

  it('shows capacity/spots-remaining in the list', async () => {
    setup([
      ['/api/activities/me/assignments', () => jsonResponse(200, { assignments: [] })],
      ['/api/activities', () => jsonResponse(200, { activities: [futureActivity] })],
    ])
    renderPage({ showToast: () => {} })
    expect(await screen.findByText(/1 spots left/)).toBeInTheDocument()
  })

  it('opening an event without an existing RSVP offers an RSVP action, and sends it', async () => {
    const fetchMock = mockFetchRouter([
      ['/api/activities/me/assignments', () => jsonResponse(200, { assignments: [] })],
      ['/api/activities/1/rsvp', () => jsonResponse(201, { assignment: { id: 5, status: 'Confirmed', is_self_rsvp: true } })],
      [/\/api\/resources\?/, () => jsonResponse(200, { resources: [] })],
      ['/api/activities', () => jsonResponse(200, { activities: [futureActivity] })],
    ])
    localStorage.clear()
    setSession('t', { id: 1, name: 'Me', role: 'volunteer' }, 'r')
    vi.stubGlobal('fetch', fetchMock)

    renderPage({ showToast: () => {} })
    await userEvent.click(await screen.findByText('Community Fair'))

    const rsvpButton = await screen.findByRole('button', { name: /rsvp to this event/i })
    await userEvent.click(rsvpButton)

    await waitFor(() => {
      const rsvpCall = fetchMock.mock.calls.find(c => c[0].includes('/rsvp') && c[1]?.method === 'POST')
      expect(rsvpCall).toBeTruthy()
    })
  })

  it('an already-RSVPed volunteer sees their status badge in the list instead of "View"', async () => {
    setup([
      ['/api/activities/me/assignments', () => jsonResponse(200, { assignments: [{ id: 5, activity_id: 1, status: 'Confirmed', is_self_rsvp: true, role: 'General Volunteer' }] })],
      ['/api/activities', () => jsonResponse(200, { activities: [futureActivity] })],
    ])
    renderPage({ showToast: () => {} })
    await screen.findByText('Community Fair')
    expect(screen.getByText('Confirmed')).toBeInTheDocument()
  })

  it('the My Assignments filter shows only staff-assigned rows, not self-RSVPs', async () => {
    const staffedActivity = { ...futureActivity, id: 3, title: 'Staffed Shift' }
    setup([
      ['/api/activities/me/assignments', () => jsonResponse(200, {
        assignments: [
          { id: 5, activity_id: 1, status: 'Confirmed', is_self_rsvp: true, role: 'General Volunteer' },
          { id: 6, activity_id: 3, status: 'Assigned', is_self_rsvp: false, role: 'Registration' },
        ],
      })],
      ['/api/activities', () => jsonResponse(200, { activities: [futureActivity, staffedActivity] })],
    ])
    renderPage({ showToast: () => {} })
    await screen.findByText('Community Fair')

    await userEvent.click(screen.getByRole('button', { name: 'My Assignments' }))
    expect(screen.getByText('Staffed Shift')).toBeInTheDocument()
    expect(screen.queryByText('Community Fair')).not.toBeInTheDocument()
  })
})
