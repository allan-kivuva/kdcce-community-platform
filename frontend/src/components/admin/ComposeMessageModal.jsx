import { useState, useEffect } from 'react'
import { Send } from 'lucide-react'
import Modal from './Modal'
import { errorMessage } from './adminHelpers'
import { apiFetch, getStoredUser } from '../../lib/api'

/** Starts a new direct conversation (or continues an existing one — the
 * backend finds-or-creates). Recipients come from /api/messages/recipients,
 * a role-scoped list — a volunteer only ever sees admin/staff names here,
 * never a general directory. Templates (admin/staff only) populate the
 * body text; they never send anything on their own. */
export default function ComposeMessageModal({ onClose, onSent, showToast }) {
  const me = getStoredUser()
  const [recipients, setRecipients] = useState([])
  const [templates, setTemplates] = useState([])
  const [recipientId, setRecipientId] = useState('')
  const [body, setBody] = useState('')
  const [sending, setSending] = useState(false)

  useEffect(() => {
    apiFetch('/api/messages/recipients').then(d => setRecipients(d.recipients)).catch(() => {})
    if (me?.role === 'admin' || me?.role === 'staff') {
      apiFetch('/api/messages/templates').then(d => setTemplates(d.templates)).catch(() => {})
    }
  }, [me?.role])

  function applyTemplate(key) {
    const template = templates.find(t => t.key === key)
    if (!template) return
    const recipient = recipients.find(r => String(r.id) === String(recipientId))
    const name = recipient ? recipient.name.split(' ')[0] : '{name}'
    setBody(template.body.replace('{name}', name))
  }

  async function send(e) {
    e.preventDefault()
    if (!recipientId || !body.trim()) return
    setSending(true)
    try {
      await apiFetch('/api/messages/conversations', { method: 'POST', body: { recipient_id: Number(recipientId), body: body.trim() } })
      showToast('Message sent')
      onSent?.()
      onClose()
    } catch (err) { showToast(errorMessage(err)) }
    finally { setSending(false) }
  }

  return <Modal title="New message" onClose={onClose}>
    <form onSubmit={send} className="grid gap-4">
      <label className="text-sm font-semibold">To
        <select value={recipientId} onChange={e => setRecipientId(e.target.value)} className="input-k mt-2" required>
          <option value="">Choose a recipient…</option>
          {recipients.map(r => <option key={r.id} value={r.id}>{r.name} ({r.role})</option>)}
        </select>
      </label>
      {templates.length > 0 && <label className="text-sm font-semibold">Template (optional)
        <select onChange={e => applyTemplate(e.target.value)} defaultValue="" className="input-k mt-2">
          <option value="">None — write your own</option>
          {templates.map(t => <option key={t.key} value={t.key}>{t.title}</option>)}
        </select>
      </label>}
      <label className="text-sm font-semibold">Message
        <textarea value={body} onChange={e => setBody(e.target.value)} rows={5} className="input-k mt-2" placeholder="Write your message..." required />
      </label>
      <button disabled={sending || !recipientId || !body.trim()} className="btn-orange justify-center disabled:opacity-60"><Send size={15} /> {sending ? 'Sending…' : 'Send message'}</button>
    </form>
  </Modal>
}
