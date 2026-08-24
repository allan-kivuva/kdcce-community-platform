import { useState, useEffect } from 'react'
import { ImageOff } from 'lucide-react'
import { fetchAuthenticatedImageUrl } from '../../lib/api'

// Read-only viewer for an assignment's photo. Never a plain <img src="...">
// to a static path — the photo has no public URL at all, so this always
// goes through the authenticated endpoint and renders whatever comes back
// (or nothing, if there's no photo or no access) as a local blob: URL.
export default function AssignmentPhoto({ basePath }) {
  const [url, setUrl] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    let objectUrl = null
    setLoading(true)
    fetchAuthenticatedImageUrl(`${basePath}/photo`).then(result => {
      if (cancelled) {
        if (result) URL.revokeObjectURL(result)
        return
      }
      objectUrl = result
      setUrl(result)
      setLoading(false)
    })
    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [basePath])

  if (loading) return null
  if (!url) return <p className="flex items-center gap-2 text-sm text-kMuted"><ImageOff size={15} /> No photo attached.</p>
  return <img src={url} alt="Assignment" className="max-h-64 w-full rounded-xl border border-kBorderSoft object-contain" />
}
