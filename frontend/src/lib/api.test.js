import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { apiFetch, ApiError, setSession, getToken, getStoredUser } from './api'

function jsonResponse(status, body) {
  return {
    status,
    ok: status >= 200 && status < 300,
    json: async () => body,
  }
}

describe('apiFetch — JWT refresh-on-401', () => {
  beforeEach(() => {
    localStorage.clear()
    setSession('old-access-token', { id: 1, name: 'A', role: 'admin' }, 'valid-refresh-token')
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('retries the original request once after a successful refresh, and returns its result', async () => {
    fetch
      .mockResolvedValueOnce(jsonResponse(401, { error: 'Token has expired' })) // original request
      .mockResolvedValueOnce(jsonResponse(200, { access_token: 'new-access-token' })) // POST /api/auth/refresh
      .mockResolvedValueOnce(jsonResponse(200, { volunteers: [] })) // retried original request

    const result = await apiFetch('/api/volunteers')

    expect(result).toEqual({ volunteers: [] })
    expect(fetch).toHaveBeenCalledTimes(3)
    // The refresh call must authenticate with the refresh token, not the access token.
    expect(fetch.mock.calls[1][0]).toContain('/api/auth/refresh')
    expect(fetch.mock.calls[1][1].headers.Authorization).toBe('Bearer valid-refresh-token')
    // The retried request must carry the newly-issued access token.
    expect(fetch.mock.calls[2][1].headers.Authorization).toBe('Bearer new-access-token')
    expect(getToken()).toBe('new-access-token')
  })

  it('retries only once — a 401 on the retried request itself is not refreshed again', async () => {
    fetch
      .mockResolvedValueOnce(jsonResponse(401, { error: 'Token has expired' })) // original
      .mockResolvedValueOnce(jsonResponse(200, { access_token: 'new-access-token' })) // refresh
      .mockResolvedValueOnce(jsonResponse(401, { error: 'Token has expired' })) // retried request, still 401

    await expect(apiFetch('/api/volunteers')).rejects.toThrow(ApiError)
    // Exactly 3 calls: original + refresh + one retry. A loop would keep calling refresh/fetch indefinitely.
    expect(fetch).toHaveBeenCalledTimes(3)
  })

  it('clears the session and throws the original 401 when the refresh token is rejected', async () => {
    fetch
      .mockResolvedValueOnce(jsonResponse(401, { error: 'Token has expired' })) // original
      .mockResolvedValueOnce(jsonResponse(401, { error: 'Token has been revoked' })) // refresh fails

    await expect(apiFetch('/api/volunteers')).rejects.toMatchObject({ status: 401 })
    expect(fetch).toHaveBeenCalledTimes(2) // original + one refresh attempt, no further retry
    expect(getStoredUser()).toBeNull()
    expect(getToken()).toBeNull()
  })

  it('does not attempt a refresh at all when no refresh token is stored', async () => {
    localStorage.clear()
    setSession('old-access-token', { id: 1, name: 'A', role: 'admin' }) // no refresh token
    fetch.mockResolvedValueOnce(jsonResponse(401, { error: 'Token has expired' }))

    await expect(apiFetch('/api/volunteers')).rejects.toMatchObject({ status: 401 })
    expect(fetch).toHaveBeenCalledTimes(1) // no refresh call made at all
    expect(getStoredUser()).toBeNull()
  })

  it('never tries to refresh a 401 coming from the refresh endpoint itself', async () => {
    fetch.mockResolvedValueOnce(jsonResponse(401, { error: 'Token has been revoked' }))

    await expect(apiFetch('/api/auth/refresh', { auth: false })).rejects.toMatchObject({ status: 401 })
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('does not attempt a refresh for a request made with auth: false (e.g. login)', async () => {
    fetch.mockResolvedValueOnce(jsonResponse(401, { error: 'Invalid email or password' }))

    await expect(apiFetch('/api/auth/login', { method: 'POST', auth: false, body: {} })).rejects.toMatchObject({ status: 401 })
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('dedupes concurrent 401s onto a single refresh call', async () => {
    fetch
      .mockResolvedValueOnce(jsonResponse(401, { error: 'expired' })) // request A
      .mockResolvedValueOnce(jsonResponse(401, { error: 'expired' })) // request B
      .mockResolvedValueOnce(jsonResponse(200, { access_token: 'new-access-token' })) // the one refresh call
      .mockResolvedValueOnce(jsonResponse(200, { a: 1 })) // retried A
      .mockResolvedValueOnce(jsonResponse(200, { b: 1 })) // retried B

    const [a, b] = await Promise.all([apiFetch('/api/a'), apiFetch('/api/b')])

    expect(a).toEqual({ a: 1 })
    expect(b).toEqual({ b: 1 })
    const refreshCalls = fetch.mock.calls.filter(c => String(c[0]).includes('/api/auth/refresh'))
    expect(refreshCalls).toHaveLength(1)
  })

  it('does not disturb a normal, successful (non-401) request', async () => {
    fetch.mockResolvedValueOnce(jsonResponse(200, { volunteers: [{ id: 1 }] }))

    const result = await apiFetch('/api/volunteers')

    expect(result).toEqual({ volunteers: [{ id: 1 }] })
    expect(fetch).toHaveBeenCalledTimes(1)
  })
})
