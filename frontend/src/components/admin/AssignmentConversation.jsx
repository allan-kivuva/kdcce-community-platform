import { useState, useEffect, useCallback } from 'react'
import { Send } from 'lucide-react'
import { apiFetch, getStoredUser } from '../../lib/api'
import { errorMessage } from '../admin/adminHelpers'

// A private, per-assignment thread — not the public contact-form Inbox
// (that's ownerless and unrelated to any resource; this is the opposite:
// exactly the assigned volunteer and admin/staff, scoped to one
// HomeVisit or AssistanceRequest). Shared between the volunteer portal
// and the admin manager screens, same reuse pattern as NotificationBell.
export default function AssignmentConversation({ basePath }) {
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [sending, setSending] = useState(false)
  const [draft, setDraft] = useState('')
  const me = getStoredUser()

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try { setMessages((await apiFetch(`${basePath}/messages`)).messages) }
    catch (err) { setError(errorMessage(err)) }
    finally { setLoading(false) }
  }, [basePath])

  useEffect(() => { load() }, [load])

  async function send(e) {
    e.preventDefault()
    const body = draft.trim()
    if (!body) return
    setSending(true)
    try {
      await apiFetch(`${basePath}/messages`, { method: 'POST', body: { body } })
      setDraft('')
      await load()
    } catch (err) { setError(errorMessage(err)) }
    finally { setSending(false) }
  }

  return <div>
    <h3 className="text-xs font-bold uppercase tracking-wide text-kMuted">Conversation</h3>
    {loading ? <p className="mt-3 text-sm text-kMuted">Loading…</p> : <>
      {error && <p className="mt-2 text-sm text-kOrange">{error}</p>}
      <div className="mt-3 max-h-64 overflow-y-auto rounded-xl border border-kBorderSoft p-3">
        {messages.length === 0 && <p className="text-sm text-kMuted">No messages yet.</p>}
        {messages.map(m => (
          <div key={m.id} className={`mb-3 max-w-[85%] rounded-xl px-3 py-2 text-sm last:mb-0 ${m.sender_id === me?.id ? 'ml-auto bg-kGreen text-white' : 'bg-kCream text-kInk'}`}>
            <div className="text-xs font-bold opacity-70">{m.sender_name}</div>
            <div className="mt-1 whitespace-pre-wrap break-words">{m.body}</div>
            <div className="mt-1 text-[10px] opacity-60">{new Date(m.created_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}</div>
          </div>
        ))}
      </div>
    </>}
    <form onSubmit={send} className="mt-3 flex gap-2">
      <input value={draft} onChange={e => setDraft(e.target.value)} className="input-k flex-1" placeholder="Write a message..." />
      <button disabled={sending || !draft.trim()} className="btn-orange shrink-0 disabled:opacity-60"><Send size={15} /></button>
    </form>
  </div>
}
