import { useState } from 'react'
import { Mail, MailOpen, Reply, Trash2 } from 'lucide-react'
import Shell from '../../components/admin/Shell'
import { LoadingState, ErrorState } from '../../components/admin/adminHelpers'
import { useApiResource } from '../../lib/useApiResource'

export default function InboxManager({ showToast }) {
  // per_page=100: this admin screen shows one flat list with no pager UI
  // (matching every other manager screen here) — a real page control can
  // be added if submission volume ever outgrows this.
  const inboxApi = useApiResource('/api/admin/inbox?per_page=100', { listKey: 'messages', itemKey: 'message' })
  const [openId, setOpenId] = useState(null)

  async function toggleRead(m) {
    try {
      await inboxApi.patch(m.id, { is_read: !m.is_read }, '/api/admin/inbox')
      showToast(m.is_read ? 'Marked as unread' : 'Marked as read')
    } catch { showToast('Could not update message') }
  }

  async function remove(m) {
    if (!window.confirm(`Delete message from ${m.name}?`)) return
    try {
      await inboxApi.remove(m.id, '/api/admin/inbox')
      showToast('Message deleted')
    } catch { showToast('Could not delete message') }
  }

  const unread = inboxApi.items.filter(m => !m.is_read).length

  return <Shell>
    <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center"><div><div className="eyebrow">Manage</div><h1 className="font-display text-3xl font-bold text-kGreen">Inbox</h1></div><div className="rounded-full bg-kTint px-4 py-2 text-sm font-bold text-kOrange">{unread} unread</div></div>
    {inboxApi.loading ? <LoadingState label="messages" /> : inboxApi.error ? <ErrorState message={inboxApi.error} onRetry={inboxApi.reload} /> : <div className="card-k mt-7 divide-y divide-kBorderSoft">
      {inboxApi.items.map(m => <div key={m.id} className="p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <button onClick={() => setOpenId(id => id === m.id ? null : m.id)} className="flex flex-1 items-center gap-3 text-left">
            {m.is_read ? <MailOpen size={18} className="text-kMuted" /> : <Mail size={18} className="text-kOrange" />}
            <div><div className={`text-sm ${m.is_read ? 'font-semibold text-kInk' : 'font-bold text-kGreen'}`}>{m.name} &middot; {m.subject}</div><div className="text-xs text-kMuted">{m.email} &middot; {m.created_at.slice(0, 10)}</div></div>
          </button>
          <div className="flex gap-3 text-xs font-semibold"><button onClick={() => toggleRead(m)} className="text-kOrange">{m.is_read ? 'Mark unread' : 'Mark read'}</button><button onClick={() => remove(m)} className="text-kMuted hover:text-red-600"><Trash2 size={16} /></button></div>
        </div>
        {openId === m.id && <div className="mt-4 rounded-xl bg-kCream p-4 text-sm leading-6 text-kInk">{m.message}<div className="mt-3"><a href={`mailto:${m.email}`} className="inline-flex items-center gap-2 text-sm font-semibold text-kOrange"><Reply size={14} /> Reply by email</a></div></div>}
      </div>)}
      {inboxApi.items.length === 0 && <p className="p-5 text-sm text-kMuted">No messages.</p>}
    </div>}
  </Shell>
}
