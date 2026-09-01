import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import userEvent from '@testing-library/user-event'
import AdminLogin from './AdminLogin'
import { ThemeProvider } from '../theme/ThemeProvider'
import { getStoredUser, clearSession } from '../lib/api'

function jsonResponse(status, body) {
  return { status, ok: status >= 200 && status < 300, json: async () => body }
}

function renderPage() {
  return render(<MemoryRouter><ThemeProvider><AdminLogin /></ThemeProvider></MemoryRouter>)
}

async function submitCredentials(email = 'admin@example.com', password = 'hunter22') {
  await userEvent.type(screen.getByLabelText(/email/i), email)
  await userEvent.type(screen.getByLabelText(/password/i), password)
  await userEvent.click(screen.getByRole('button', { name: /sign in/i }))
}

describe('AdminLogin', () => {
  afterEach(() => { vi.unstubAllGlobals(); clearSession() })

  it('signs a normal (no-2FA) account in directly', async () => {
    const fetchMock = vi.fn(() => Promise.resolve(jsonResponse(200, {
      user: { id: 1, name: 'Admin', role: 'admin' }, access_token: 'a', refresh_token: 'r',
    })))
    vi.stubGlobal('fetch', fetchMock)

    renderPage()
    await submitCredentials()

    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/api/auth/login'), expect.objectContaining({ method: 'POST' }))
    expect(getStoredUser()).toMatchObject({ id: 1, role: 'admin' })
  })

  it('shows a code-entry step when the account has 2FA enabled, then verifies it', async () => {
    const fetchMock = vi.fn((url) => {
      if (url.includes('/api/auth/login')) return Promise.resolve(jsonResponse(200, { two_factor_required: true, challenge_token: 'chal-123' }))
      if (url.includes('/api/auth/2fa/verify-login')) return Promise.resolve(jsonResponse(200, {
        user: { id: 2, name: 'Admin 2FA', role: 'admin' }, access_token: 'a2', refresh_token: 'r2',
      }))
      throw new Error('unexpected fetch: ' + url)
    })
    vi.stubGlobal('fetch', fetchMock)

    renderPage()
    await submitCredentials()

    expect(await screen.findByText(/verify it's you/i)).toBeInTheDocument()
    await userEvent.type(screen.getByLabelText(/6-digit code/i), '123456')
    await userEvent.click(screen.getByRole('button', { name: /verify/i }))

    const verifyCall = fetchMock.mock.calls.find(c => c[0].includes('/api/auth/2fa/verify-login'))
    expect(JSON.parse(verifyCall[1].body)).toEqual({ challenge_token: 'chal-123', code: '123456' })
    expect(getStoredUser()).toMatchObject({ id: 2, role: 'admin' })
  })

  it('shows an error and stays on the code step when the OTP is wrong', async () => {
    const fetchMock = vi.fn((url) => {
      if (url.includes('/api/auth/login')) return Promise.resolve(jsonResponse(200, { two_factor_required: true, challenge_token: 'chal-1' }))
      if (url.includes('/api/auth/2fa/verify-login')) return Promise.resolve(jsonResponse(401, { error: 'Invalid verification code' }))
      throw new Error('unexpected fetch: ' + url)
    })
    vi.stubGlobal('fetch', fetchMock)

    renderPage()
    await submitCredentials()
    await screen.findByText(/verify it's you/i)
    await userEvent.type(screen.getByLabelText(/6-digit code/i), '000000')
    await userEvent.click(screen.getByRole('button', { name: /verify/i }))

    expect(await screen.findByText('Invalid verification code')).toBeInTheDocument()
    expect(getStoredUser()).toBeNull()
  })

  it('can switch to a recovery code instead of an authenticator code', async () => {
    const fetchMock = vi.fn((url) => {
      if (url.includes('/api/auth/login')) return Promise.resolve(jsonResponse(200, { two_factor_required: true, challenge_token: 'chal-2' }))
      if (url.includes('/api/auth/2fa/recovery')) return Promise.resolve(jsonResponse(200, {
        user: { id: 3, name: 'Recovered Admin', role: 'admin' }, access_token: 'a3', refresh_token: 'r3',
      }))
      throw new Error('unexpected fetch: ' + url)
    })
    vi.stubGlobal('fetch', fetchMock)

    renderPage()
    await submitCredentials()
    await screen.findByText(/verify it's you/i)

    await userEvent.click(screen.getByRole('button', { name: /use a recovery code/i }))
    await userEvent.type(screen.getByLabelText(/recovery code/i), 'abcde-12345')
    await userEvent.click(screen.getByRole('button', { name: /verify/i }))

    const recoveryCall = fetchMock.mock.calls.find(c => c[0].includes('/api/auth/2fa/recovery'))
    expect(JSON.parse(recoveryCall[1].body)).toEqual({ challenge_token: 'chal-2', recovery_code: 'abcde-12345' })
    expect(getStoredUser()).toMatchObject({ id: 3 })
  })

  it('shows an error banner on bad credentials without ever entering the 2FA step', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(jsonResponse(401, { error: 'Invalid email or password' }))))
    renderPage()
    await submitCredentials()
    expect(await screen.findByText('Invalid email or password')).toBeInTheDocument()
    expect(screen.queryByText(/verify it's you/i)).not.toBeInTheDocument()
  })
})
