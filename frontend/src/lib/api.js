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

function setAccessToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
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

// Dedupes concurrent 401s (e.g. two polling requests landing the same
// moment an access token expires) onto a single in-flight refresh call,
// rather than firing one refresh per failed request.
let refreshPromise = null

/** Exchanges the stored refresh token for a new access token via the
 * existing POST /api/auth/refresh (unchanged — this just calls it from
 * the client for the first time). Returns true and updates localStorage
 * on success; false on any failure (no refresh token stored, or the
 * server rejected it as expired/revoked/invalid) — never throws, so
 * callers can treat "couldn't refresh" as a plain signal to give up
 * rather than an error to handle. */
function refreshAccessToken() {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      const refreshToken = getRefreshToken()
      if (!refreshToken) return false
      try {
        const res = await fetch(`${API_URL}/api/auth/refresh`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${refreshToken}` },
        })
        if (!res.ok) return false
        const payload = await res.json().catch(() => null)
        if (!payload?.access_token) return false
        setAccessToken(payload.access_token)
        return true
      } catch {
        return false
      }
    })().finally(() => { refreshPromise = null })
  }
  return refreshPromise
}

/**
 * Thin fetch wrapper: prefixes VITE_API_URL, attaches the stored JWT (if
 * any) and JSON headers, and normalizes non-2xx responses into a thrown
 * ApiError with the backend's error/details payload attached.
 *
 * On a 401 from an authenticated request (not a login/register/refresh
 * call — those pass auth:false or are the refresh call itself), this
 * transparently tries POST /api/auth/refresh once and, if that succeeds,
 * retries the original request exactly once with the new access token —
 * `_isRetry` is only ever set by that one retry call, never by an outside
 * caller, which is what keeps this to a single attempt instead of a loop.
 * If there's no refresh token, or the server rejects it, the session is
 * cleared and the original 401 is thrown as before — every existing
 * call site's "on 401, clearSession + redirect to login" handling
 * (useApiResource, VolunteerPortal, ...) still fires exactly as it did
 * before this change; it just now only fires for a genuinely-dead
 * session instead of every hour on a natural access-token expiry.
 */
export async function apiFetch(path, { method = 'GET', body, auth = true, _isRetry = false } = {}) {
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

  if (res.status === 401 && auth && !_isRetry && path !== '/api/auth/refresh') {
    const refreshed = await refreshAccessToken()
    if (refreshed) return apiFetch(path, { method, body, auth, _isRetry: true })
    clearSession()
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
export async function downloadFile(path, filename, _isRetry = false) {
  const token = getToken()
  const res = await fetch(`${API_URL}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {}
  })
  if (res.status === 401 && !_isRetry) {
    const refreshed = await refreshAccessToken()
    if (refreshed) return downloadFile(path, filename, true)
    clearSession()
  }
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

/** Posts an arbitrary multipart/form-data FormData (a file plus any other
 * fields, e.g. a document's title/type/dates alongside its file).
 * Deliberately not apiFetch: that always JSON.stringifies the body and
 * sets Content-Type: application/json, neither of which is right here —
 * the browser must set its own multipart boundary in the Content-Type
 * header. The shared low-level helper behind both uploadFile (single
 * file, no other fields — assignment photos) and uploadForm (a full form
 * — volunteer documents) below, so both get the same auth/refresh-retry/
 * error handling from one place. */
async function uploadFormData(path, formData, _isRetry = false) {
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

  if (res.status === 401 && !_isRetry) {
    const refreshed = await refreshAccessToken()
    if (refreshed) return uploadFormData(path, formData, true)
    clearSession()
  }

  const payload = await res.json().catch(() => null)
  if (!res.ok) {
    throw new ApiError(payload?.error || `Upload failed (${res.status})`, res.status, payload?.details)
  }
  return payload
}

export async function uploadFile(path, fieldName, file) {
  const formData = new FormData()
  formData.append(fieldName, file)
  return uploadFormData(path, formData)
}

/** For a form with a file plus other fields (see MyDocuments.jsx) — pass
 * a FormData built straight from the <form>'s own fields via `new
 * FormData(formElement)`, file input included. */
export async function uploadForm(path, formData) {
  return uploadFormData(path, formData)
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
