import { useState, useEffect } from 'react'
import { Megaphone } from 'lucide-react'
import Modal from './Modal'
import { errorMessage } from './adminHelpers'
import { apiFetch } from '../../lib/api'

const AUDIENCES = ['All', 'Volunteers', 'Verified Volunteers', 'Staff', 'Admin', 'Selected']

/** Sends one message to a resolved group via POST /api/broadcasts — a
 * client-generated token guards a double-click or network retry from
 * fanning out the same broadcast twice (the backend treats a repeat
 * token as "already sent, here's the original" rather than sending
 * again). */
export default function BroadcastModal({ onClose, showToast }) {
  const [audience, setAudience] = useState('All')
  const [volunteers, setVolunteers] = useState([])
  const [selectedIds, setSelectedIds] = useState([])
  const [title, setTitle] = useState('')
  const [message, setMessage] = useState('')
  const [sending, setSending] = useState(false)
  const [clientToken] = useState(() => `${Date.now()}-${Math.random().toString(36).slice(2)}`)

  useEffect(() => {
    if (audience === 'Selected' && volunteers.length === 0) {
      apiFetch('/api/volunteers').then(d => setVolunteers(d.volunteers)).catch(() => {})
    }
  }, [audience, volunteers.length])

  function toggleSelected(id) {
    setSelectedIds(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id])
  }

  async function send(e) {
    e.preventDefault()
    if (audience === 'Selected' && selectedIds.length === 0) { showToast('Choose at least one recipient'); return }
    setSending(true)
    try {
      const resp = await apiFetch('/api/broadcasts', {
        method: 'POST',
        body: { audience_type: audience, title, message, selected_user_ids: audience === 'Selected' ? selectedIds : undefined, client_token: clientToken },
      })
      showToast(`Sent to ${resp.broadcast.recipient_count} recipient${resp.broadcast.recipient_count === 1 ? '' : 's'}`)
      onClose()
    } catch (err) { showToast(errorMessage(err)) }
    finally { setSending(false) }
  }

  return <Modal title="Send broadcast" onClose={onClose}>
    <form onSubmit={send} className="grid gap-4">
      <label className="text-sm font-semibold">Audience
        <select value={audience} onChange={e => setAudience(e.target.value)} className="input-k mt-2">
          {AUDIENCES.map(a => <option key={a}>{a}</option>)}
        </select>
      </label>
      {audience === 'Selected' && <div className="max-h-40 overflow-y-auto rounded-xl border border-kBorder p-2">
        {volunteers.length === 0 && <p className="p-2 text-xs text-kMuted">Loading volunteers…</p>}
        {volunteers.map(v => <label key={v.id} className="flex items-center gap-2 px-2 py-1.5 text-sm"><input type="checkbox" checked={selectedIds.includes(v.id)} onChange={() => toggleSelected(v.id)} className="h-4 w-4" /> {v.name}</label>)}
      </div>}
      <label className="text-sm font-semibold">Title<input value={title} onChange={e => setTitle(e.target.value)} className="input-k mt-2" required /></label>
      <label className="text-sm font-semibold">Message<textarea value={message} onChange={e => setMessage(e.target.value)} rows={4} className="input-k mt-2" required /></label>
      <button disabled={sending || !title.trim() || !message.trim()} className="btn-orange justify-center disabled:opacity-60"><Megaphone size={15} /> {sending ? 'Sending…' : 'Send broadcast'}</button>
    </form>
  </Modal>
}
