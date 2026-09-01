import { Navigate, useLocation } from 'react-router-dom'
import { getStoredUser } from '../lib/api'

/** Route-level auth guard — checks the locally stored session (not an API
 * call) so a redirect happens immediately on navigation, not only after
 * some data fetch happens to 401. That reactive path still exists
 * separately (apiFetch's own refresh-then-redirect, useApiResource's
 * 401 handling, VolunteerPortal's own check on its profile fetch) and is
 * left untouched — this is a second, independent line of defense at the
 * route level, not a replacement for it.
 *
 * `roles`, if given, restricts the route to those roles; a signed-in user
 * of the wrong role is sent to their own home area (matching the same
 * role -> landing-page mapping AdminLogin already uses on sign-in), not
 * back to the login page — they don't need to log in again, they're just
 * not allowed on this particular route. */
export default function ProtectedRoute({ roles, children }) {
  const location = useLocation()
  const user = getStoredUser()

  if (!user) {
    return <Navigate to="/admin/login" replace state={{ from: location }} />
  }
  if (roles && !roles.includes(user.role)) {
    return <Navigate to={_homeFor(user.role)} replace />
  }
  return children
}

// Same role -> landing-page mapping AdminLogin uses on sign-in — kept
// here too since this is the OTHER place a role's home area is decided
// (bouncing a signed-in user off a route they're not allowed on).
function _homeFor(role) {
  if (role === 'volunteer') return '/volunteer'
  if (role === 'family') return '/family'
  return '/admin'
}
