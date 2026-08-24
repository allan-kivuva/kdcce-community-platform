import { useState, useEffect, useCallback } from 'react'
import { Star } from 'lucide-react'
import { apiFetch, getStoredUser } from '../../lib/api'
import { errorMessage } from './adminHelpers'

function Stars({ value, onChange, size = 20 }) {
  const interactive = typeof onChange === 'function'
  return <div className="flex gap-1">
    {[1, 2, 3, 4, 5].map(n => (
      <button
        key={n}
        type="button"
        disabled={!interactive}
        onClick={() => interactive && onChange(n)}
        className={interactive ? 'cursor-pointer' : 'cursor-default'}
        aria-label={`${n} star${n > 1 ? 's' : ''}`}
      >
        <Star size={size} className={n <= value ? 'fill-kOrange text-kOrange' : 'text-kBorderSoft'} />
      </button>
    ))}
  </div>
}

// Admin-only to submit (matches the backend's roles_required("admin"),
// deliberately not the usual admin+staff pair) — visible read-only to
// staff and to the assigned volunteer via the same GET the backend
// already scopes correctly. Only relevant once status is Completed.
export default function AssignmentReview({ basePath, status, showToast }) {
  const isAdmin = getStoredUser()?.role === 'admin'
  const [review, setReview] = useState(null)
  const [loading, setLoading] = useState(true)
  const [rating, setRating] = useState(0)
  const [comment, setComment] = useState('')
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await apiFetch(`${basePath}/review`)
      setReview(res.review)
      setRating(res.review.rating)
      setComment(res.review.comment || '')
    } catch {
      setReview(null)
    } finally {
      setLoading(false)
    }
  }, [basePath])

  useEffect(() => { load() }, [load])

  async function submit(e) {
    e.preventDefault()
    if (!rating) { showToast('Choose a star rating first'); return }
    setSaving(true)
    try {
      await apiFetch(`${basePath}/review`, { method: 'POST', body: { rating, comment: comment || null } })
      showToast('Review submitted')
      load()
    } catch (err) { showToast(errorMessage(err)) }
    finally { setSaving(false) }
  }

  if (status !== 'Completed') return null
  if (loading) return null

  return <div>
    <h3 className="text-xs font-bold uppercase tracking-wide text-kMuted">Admin review</h3>
    {!isAdmin ? (
      review ? <div className="mt-2"><Stars value={review.rating} /><p className="mt-2 text-sm text-kMuted">{review.comment || 'No comment left.'}</p><p className="mt-1 text-xs text-kMuted">Reviewed by {review.reviewed_by}</p></div>
        : <p className="mt-2 text-sm text-kMuted">Not yet reviewed.</p>
    ) : (
      <form onSubmit={submit} className="mt-2 grid gap-3">
        <Stars value={rating} onChange={setRating} />
        <textarea value={comment} onChange={e => setComment(e.target.value)} rows={2} className="input-k" placeholder="Comment on how this was handled (optional)" />
        <button disabled={saving} className="btn-orange w-fit disabled:opacity-60">{saving ? 'Saving…' : review ? 'Update review' : 'Submit review'}</button>
        {review && <p className="text-xs text-kMuted">Last reviewed by {review.reviewed_by}</p>}
      </form>
    )}
  </div>
}
