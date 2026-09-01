import { useState, useEffect, useCallback } from 'react'
import { AlertCircle, HandHeart, Home, MessageSquarePlus, Megaphone, User } from 'lucide-react'
import Shell from '../../components/admin/Shell'
import ConversationSplitView from '../../components/admin/ConversationSplitView'
import DirectConversationThread from '../../components/admin/DirectConversationThread'
import AssignmentConversation from '../../components/admin/AssignmentConversation'
import ComposeMessageModal from '../../components/admin/ComposeMessageModal'
import BroadcastModal from '../../components/admin/BroadcastModal'
import { timeAgo, errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch } from '../../lib/api'

const KIND_ICON = { direct: <User size={18} />, home_visit: <Home size={16} />, assistance_request: <HandHeart size={16} /> }
const KIND_LABEL = { home_visit: 'Home Visit', assistance_request: 'Assistance Request' }

export default function MessagesManager({ showToast }) {
  const [direct, setDirect] = useState([])
  const [assignmentThreads, setAssignmentThreads] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedKey, setSelectedKey] = useState(null)
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('all') // all | needs-reply
  const [unresolvedIds, setUnresolvedIds] = useState(new Set())
  const [composing, setComposing] = useState(false)
  const [broadcasting, setBroadcasting] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [d, a, u] = await Promise.all([
        apiFetch('/api/messages/conversations'),
        apiFetch('/api/messages/assignment-conversations'),
        apiFetch('/api/messages/unresolved'),
      ])
      setDirect(d.conversations)
      setAssignmentThreads(a.conversations)
      setUnresolvedIds(new Set(u.unresolved.map(x => x.conversation_id)))
    } catch (err) { setError(errorMessage(err)) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const allItems = [
    ...direct.map(c => ({
      key: `direct-${c.id}`, id: c.id, kind: 'direct', icon: KIND_ICON.direct,
      title: c.other_user.name, subtitle: c.other_user.role,
      preview: c.last_message?.body, timestamp: timeAgo(c.updated_at), updatedAt: c.updated_at,
      unread: c.unread_count > 0, badge: c.unread_count, needsReply: unresolvedIds.has(c.id),
    })),
    ...assignmentThreads.map(t => ({
      key: `${t.kind}-${t.id}`, id: t.id, kind: t.kind, icon: KIND_ICON[t.kind],
      title: t.elderly_member_name, subtitle: `${KIND_LABEL[t.kind]} · ${t.assigned_to || 'Unassigned'}`,
      preview: t.last_message?.body, timestamp: timeAgo(t.updated_at), updatedAt: t.updated_at,
      unread: false, needsReply: false,
    })),
  ].sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt))

  // The currently-open thread is always found from the unfiltered list —
  // otherwise replying to a "Needs Reply" conversation (which correctly
  // makes it drop out of that filter, since it's now resolved) would
  // yank the thread the admin is actively looking at out from under them.
  // The filter/search only decide what's browsable in the left list.
  const selected = allItems.find(it => it.key === selectedKey)
  const items = allItems
    .filter(it => filter !== 'needs-reply' || it.needsReply)
    .filter(it => !search || it.title.toLowerCase().includes(search.toLowerCase()) || it.subtitle.toLowerCase().includes(search.toLowerCase()))

  function selectAndClearUnread(key) {
    setSelectedKey(key)
    if (key) setDirect(prev => prev.map(c => `direct-${c.id}` === key ? { ...c, unread_count: 0 } : c))
  }

  return <Shell>
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div><div className="eyebrow">Communication</div><h1 className="font-display text-3xl font-bold text-kGreen">Messages</h1></div>
      <div className="flex gap-2">
        <button onClick={() => setBroadcasting(true)} className="flex items-center gap-2 rounded-xl border border-kBorder px-4 py-2.5 text-sm font-bold text-kMuted hover:bg-kCream"><Megaphone size={16} /> Broadcast</button>
        <button onClick={() => setComposing(true)} className="btn-orange"><MessageSquarePlus size={16} /> New message</button>
      </div>
    </div>

    <div className="mt-5 flex gap-2">
      <button onClick={() => setFilter('all')} className={`rounded-full px-4 py-1.5 text-xs font-bold ${filter === 'all' ? 'bg-kOrange text-white' : 'bg-kCream text-kMuted'}`}>All</button>
      <button onClick={() => setFilter('needs-reply')} className={`flex items-center gap-1.5 rounded-full px-4 py-1.5 text-xs font-bold ${filter === 'needs-reply' ? 'bg-kOrange text-white' : 'bg-kCream text-kMuted'}`}><AlertCircle size={12} /> Needs Reply {unresolvedIds.size > 0 && `(${unresolvedIds.size})`}</button>
    </div>

    <ConversationSplitView
      items={items} selectedKey={selectedKey} onSelect={selectAndClearUnread}
      loading={loading} error={error} onRetry={load}
      search={{ value: search, onChange: setSearch }}
      emptyMessage={filter === 'needs-reply' ? 'Nothing waiting for a reply.' : 'No conversations yet.'}
    >
      {selected?.kind === 'direct' && <DirectConversationThread conversationId={selected.id} otherUser={{ name: selected.title, role: selected.subtitle }} onRead={load} />}
      {selected && selected.kind !== 'direct' && <div className="flex-1 overflow-y-auto p-4">
        <div className="mb-3"><div className="text-sm font-bold text-kInk">{selected.title}</div><div className="text-xs text-kMuted">{selected.subtitle}</div></div>
        <AssignmentConversation basePath={`/api/${selected.kind === 'home_visit' ? 'home-visits' : 'assistance-requests'}/${selected.id}`} />
      </div>}
    </ConversationSplitView>

    {composing && <ComposeMessageModal onClose={() => setComposing(false)} onSent={load} showToast={showToast} />}
    {broadcasting && <BroadcastModal onClose={() => setBroadcasting(false)} showToast={showToast} />}
  </Shell>
}
