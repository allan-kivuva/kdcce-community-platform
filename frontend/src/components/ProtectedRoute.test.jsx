import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import ProtectedRoute from './ProtectedRoute'
import { setSession, clearSession } from '../lib/api'

function renderAt(path, roles) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/admin/login" element={<div>Login page</div>} />
        <Route path="/admin" element={<div>Admin home</div>} />
        <Route path="/volunteer" element={<div>Volunteer home</div>} />
        <Route path="/family" element={<div>Family home</div>} />
        <Route path="/protected" element={<ProtectedRoute roles={roles}><div>Protected content</div></ProtectedRoute>} />
      </Routes>
    </MemoryRouter>
  )
}

describe('ProtectedRoute', () => {
  beforeEach(() => { clearSession() })

  it('redirects to /admin/login when no user is stored', () => {
    renderAt('/protected')
    expect(screen.getByText('Login page')).toBeInTheDocument()
  })

  it('renders the protected content for an authenticated user with no role restriction', () => {
    setSession('t', { id: 1, name: 'A', role: 'admin' }, 'r')
    renderAt('/protected')
    expect(screen.getByText('Protected content')).toBeInTheDocument()
  })

  it('renders the protected content when the user has an allowed role', () => {
    setSession('t', { id: 1, name: 'A', role: 'staff' }, 'r')
    renderAt('/protected', ['admin', 'staff'])
    expect(screen.getByText('Protected content')).toBeInTheDocument()
  })

  it('redirects a volunteer away from an admin-only route to /volunteer, not the login page', () => {
    setSession('t', { id: 2, name: 'V', role: 'volunteer' }, 'r')
    renderAt('/protected', ['admin', 'staff'])
    expect(screen.getByText('Volunteer home')).toBeInTheDocument()
  })

  it('redirects an admin away from a volunteer-only route to /admin, not the login page', () => {
    setSession('t', { id: 1, name: 'A', role: 'admin' }, 'r')
    renderAt('/protected', ['volunteer'])
    expect(screen.getByText('Admin home')).toBeInTheDocument()
  })

  it('renders the protected content for a family account with an allowed role', () => {
    setSession('t', { id: 3, name: 'F', role: 'family' }, 'r')
    renderAt('/protected', ['family'])
    expect(screen.getByText('Protected content')).toBeInTheDocument()
  })

  it('redirects a family account away from an admin-only route to /family, not /admin (regression: used to bounce to /admin, which itself requires admin/staff, causing a redirect loop)', () => {
    setSession('t', { id: 3, name: 'F', role: 'family' }, 'r')
    renderAt('/protected', ['admin', 'staff'])
    expect(screen.getByText('Family home')).toBeInTheDocument()
  })

  it('redirects an admin away from a family-only route to /admin, not /family', () => {
    setSession('t', { id: 1, name: 'A', role: 'admin' }, 'r')
    renderAt('/protected', ['family'])
    expect(screen.getByText('Admin home')).toBeInTheDocument()
  })
})
