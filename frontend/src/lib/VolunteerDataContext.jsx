import { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { apiFetch } from './api'
import { errorMessage } from '../components/admin/adminHelpers'

const VolunteerDataContext = createContext(null)

// Every volunteer-portal page that needs "my assignments/followups/elderly
// members" was independently re-fetching the same four endpoints on every
// navigation — that's what caused the visible loading flash switching
// between Dashboard/Activity/Performance/Messages/Elderly Members. This
// fetches them once per portal session and shares the result; pages read
// from here instead of firing their own requests, and call reload() after
// a mutation (accept/start/complete/etc.) to refresh the shared copy.
export function VolunteerDataProvider({ children }) {
  const [state, setState] = useState({ loading: true, error: '', visits: [], requests: [], followups: [], elderlyMembers: [] })

  const reload = useCallback(async () => {
    setState(s => ({ ...s, error: '' }))
    try {
      const [v, r, f, e] = await Promise.all([
        apiFetch('/api/home-visits'),
        apiFetch('/api/assistance-requests'),
        apiFetch('/api/followups'),
        apiFetch('/api/volunteers/me/elderly-members'),
      ])
      setState({ loading: false, error: '', visits: v.visits, requests: r.requests, followups: f.followups, elderlyMembers: e.elderly_members })
    } catch (err) {
      setState(s => ({ ...s, loading: false, error: errorMessage(err) }))
    }
  }, [])

  useEffect(() => { reload() }, [reload])

  return <VolunteerDataContext.Provider value={{ ...state, reload }}>{children}</VolunteerDataContext.Provider>
}

export function useVolunteerData() {
  const ctx = useContext(VolunteerDataContext)
  if (!ctx) throw new Error('useVolunteerData must be used within VolunteerDataProvider')
  return ctx
}
