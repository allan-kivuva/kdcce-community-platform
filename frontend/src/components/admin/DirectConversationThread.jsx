import { useState, useEffect, useCallback, useRef } from 'react'
import { Send } from 'lucide-react'
import { apiFetch, getStoredUser } from '../../lib/api'
import { errorMessage } from './adminHelpers'

/** One open direct-message thread — mirrors AssignmentConversation's
 * layout/interaction (same reply-box pattern, same sender-side bubble
 * styling) but talks to the general /api/messages endpoints instead of
 * a per-assignment one, and marks the thread read on open plus polls
 * every 20s while it stays open (per this phase's "15-30s only while a
 * conversation is open" polling rule — the shared 60s badge poll in
 * useCommunicationCounts covers everywhere else). */
export default function DirectConversationThread({ conversationId, otherUser, onRead }) {
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [sending, setSending] = useState(false)
  const [draft, setDraft] = useState('')
  const me = getStoredUser()
  const bottomRef = useRef(null)

  const load = useCallback(async () => {
    try {
      const data = await apiFetch(`/api/messages/conversations/${conversationId}`)
      setMessages(data.conversation.messages)
    } catch (err) { setError(errorMessage(err)) }
    finally { setLoading(false) }
  }, [conversationId])

  useEffect(() => {
    setLoading(true)
    setError('')
    load()
    apiFetch(`/api/messages/conversations/${conversationId}/read`, { method: 'PATCH' }).then(() => onRead?.()).catch(() => {})
    const interval = setInterval(load, 20000)
    return () => clearInterval(interval)
  }, [conversationId, load, onRead])

  useEffect(() => { bottomRef.current?.scrollIntoView({ block: 'nearest' }) }, [messages.length])

  async function send(e) {
    e.preventDefault()
    const body = draft.trim()
    if (!body) return
    setSending(true)
    try {
      await apiFetch(`/api/messages/conversations/${conversationId}/messages`, { method: 'POST', body: { body } })
      setDraft('')
      await load()
      // Sending can flip this conversation's unresolved/last-message
      // state (e.g. an admin reply clears it from "Needs Reply") — the
      // parent's list/badge data needs the same refresh a mark-as-read
      // triggers, not just this thread's own messages.
      onRead?.()
    } catch (err) { setError(errorMessage(err)) }
    finally { setSending(false) }
  }

  return <div className="flex flex-1 flex-col">
    <div className="border-b border-kBorderSoft p-4">
      <div className="text-sm font-bold text-kInk">{otherUser.name}</div>
      <div className="text-xs capitalize text-kMuted">{otherUser.role}</div>
    </div>
    <div className="flex-1 overflow-y-auto p-4">
      {loading ? <p className="text-sm text-kMuted">Loading…</p> : <>
        {error && <p className="mb-2 text-sm text-kOrange">{error}</p>}
        {messages.length === 0 && <p className="text-sm text-kMuted">No messages yet — say hello.</p>}
        {messages.map(m => <div key={m.id} className={`mb-3 max-w-[75%] rounded-xl px-3 py-2 text-sm ${m.sender_id === me?.id ? 'ml-auto bg-kGreen text-white' : 'bg-kCream text-kInk'}`}>
          <div className="text-xs font-bold opacity-70">{m.sender_name}</div>
          <div className="mt-1 whitespace-pre-wrap break-words">{m.body}</div>
          <div className="mt-1 text-[10px] opacity-60">{new Date(m.created_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}</div>
        </div>)}
        <div ref={bottomRef} />
      </>}
    </div>
    <form onSubmit={send} className="flex gap-2 border-t border-kBorderSoft p-3">
      <input value={draft} onChange={e => setDraft(e.target.value)} className="input-k flex-1" placeholder="Write a message..." />
      <button disabled={sending || !draft.trim()} className="btn-orange shrink-0 disabled:opacity-60"><Send size={15} /></button>
    </form>
  </div>
}
