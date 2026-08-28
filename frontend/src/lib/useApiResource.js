import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiFetch, clearSession, ApiError } from './api'
import { errorMessage } from '../components/admin/adminHelpers'

// One small hook per resource: fetch on mount, expose CRUD helpers that
// call the API and then patch local state from the server's response
// (never from what was merely submitted), plus a 401 → sign-out redirect.
export function useApiResource(path, { listKey, itemKey }) {
  const navigate = useNavigate()
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await apiFetch(path)
      setItems(data[listKey])
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) { clearSession(); navigate('/admin/login'); return }
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [path, listKey, navigate])

  useEffect(() => { load() }, [load])

  async function create(body, basePath) {
    const data = await apiFetch(basePath ?? path, { method: 'POST', body })
    setItems(prev => [data[itemKey], ...prev])
    return data[itemKey]
  }
  async function patch(id, body, basePath) {
    const data = await apiFetch(`${basePath ?? path}/${id}`, { method: 'PATCH', body })
    setItems(prev => prev.map(it => it.id === id ? data[itemKey] : it))
    return data[itemKey]
  }
  async function remove(id, basePath) {
    await apiFetch(`${basePath ?? path}/${id}`, { method: 'DELETE' })
    setItems(prev => prev.filter(it => it.id !== id))
  }

  return { items, loading, error, reload: load, create, patch, remove }
}
