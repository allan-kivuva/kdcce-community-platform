import { useEffect, useState } from 'react'
import { apiFetch, ApiError } from './api'

/** Fetches a public list endpoint on mount and unwraps `data[listKey]`. */
export function useApiList(path, listKey) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')
    apiFetch(path, { auth: false })
      .then(data => { if (!cancelled) setItems(data[listKey]) })
      .catch(err => { if (!cancelled) setError(err instanceof ApiError ? err.message : 'Could not load content.') })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [path, listKey])

  return { items, loading, error }
}
