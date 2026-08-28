const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000'
const TOKEN_KEY = 'kdcce_token'
const REFRESH_TOKEN_KEY = 'kdcce_refresh_token'
const USER_KEY = 'kdcce_user'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_TOKEN_KEY)
}

export function getStoredUser() {
  const raw = localStorage.getItem(USER_KEY)
  return raw ? JSON.parse(raw) : null
}

export function setSession(token, user, refreshToken) {
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(USER_KEY, JSON.stringify(user))
  if (refreshToken) localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)
}

/** Revokes the current session's tokens server-side, then clears local storage.
 * Safe to call even with an already-invalid/expired token — a failed revoke
 * still falls through to the local clear, since signing out locally must
 * never get stuck behind a network call. */
export async function endSession() {
  const token = getToken()
  const refreshToken = getRefreshToken()
  if (token) {
    try {
      await apiFetch('/api/auth/logout', { method: 'POST', body: refreshToken ? { refresh_token: refreshToken } : undefined })
    } catch { /* token already invalid/expired, or offline — clear locally regardless */ }
  }
  clearSession()
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

export class ApiError extends Error {
  constructor(message, status, details) {
    super(message)
    this.status = status
    this.details = details
  }
}

/**
 * Thin fetch wrapper: prefixes VITE_API_URL, attaches the stored JWT (if
 * any) and JSON headers, and normalizes non-2xx responses into a thrown
 * ApiError with the backend's error/details payload attached.
 */
export async function apiFetch(path, { method = 'GET', body, auth = true } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  if (auth) {
    const token = getToken()
    if (token) headers.Authorization = `Bearer ${token}`
  }

  let res
  try {
    res = await fetch(`${API_URL}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined
    })
  } catch (networkErr) {
    throw new ApiError('Could not reach the server. Check your connection and try again.', 0)
  }

  if (res.status === 204) return null

  let payload = null
  try { payload = await res.json() } catch { /* empty body */ }

  if (!res.ok) {
    throw new ApiError(payload?.error || `Request failed (${res.status})`, res.status, payload?.details)
  }
  return payload
}

/** Downloads an authenticated file response (e.g. CSV export) as a browser download. */
export async function downloadFile(path, filename) {
  const token = getToken()
  const res = await fetch(`${API_URL}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {}
  })
  if (!res.ok) {
    const payload = await res.json().catch(() => null)
    throw new ApiError(payload?.error || `Download failed (${res.status})`, res.status)
  }
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

/** Uploads a file as multipart/form-data. Deliberately not apiFetch: that
 * always JSON.stringifies the body and sets Content-Type: application/json,
 * neither of which is right for a file upload — the browser must set its
 * own multipart boundary in the Content-Type header. */
export async function uploadFile(path, fieldName, file) {
  const formData = new FormData()
  formData.append(fieldName, file)
  const token = getToken()

  let res
  try {
    res = await fetch(`${API_URL}${path}`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    })
  } catch {
    throw new ApiError('Could not reach the server. Check your connection and try again.', 0)
  }

  const payload = await res.json().catch(() => null)
  if (!res.ok) {
    throw new ApiError(payload?.error || `Upload failed (${res.status})`, res.status, payload?.details)
  }
  return payload
}

/** Fetches a private, authenticated image and returns a local blob: URL
 * for it — a plain <img src="..."> can't send an Authorization header, so
 * this is the only way to display a photo the backend gates by auth.
 * Caller is responsible for URL.revokeObjectURL(...) when done with it
 * (see AssignmentPhoto's cleanup effect). Returns null on any failure
 * (no photo, no access, etc.) rather than throwing — callers treat "no
 * photo to show" as a normal state, not an error to surface.*/
export async function fetchAuthenticatedImageUrl(path) {
  const token = getToken()
  try {
    const res = await fetch(`${API_URL}${path}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {}
    })
    if (!res.ok) return null
    const blob = await res.blob()
    return URL.createObjectURL(blob)
  } catch {
    return null
  }
}
