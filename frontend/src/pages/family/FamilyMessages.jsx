import { useState, useEffect, useCallback } from 'react'
import { MessageSquarePlus, User } from 'lucide-react'
import FamilyShell from '../../components/family/FamilyShell'
import ConversationSplitView from '../../components/admin/ConversationSplitView'
import DirectConversationThread from '../../components/admin/DirectConversationThread'
import ComposeMessageModal from '../../components/admin/ComposeMessageModal'
import { errorMessage, timeAgo } from '../../components/admin/adminHelpers'
import { apiFetch } from '../../lib/api'

export default function FamilyMessages({ showToast }) {
  const [conversations, setConversations] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedId, setSelectedId] = useState(null)
  const [search, setSearch] = useState('')
  const [composing, setComposing] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try { setConversations((await apiFetch('/api/messages/conversations')).conversations) }
    catch (err) { setError(errorMessage(err)) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const items = conversations
    .filter(c => c.other_user.name.toLowerCase().includes(search.toLowerCase()))
    .map(c => ({
      key: c.id, title: c.other_user.name, subtitle: c.other_user.role, icon: <User size={16} />,
      preview: c.last_message?.body, timestamp: c.updated_at ? timeAgo(c.updated_at) : '',
      unread: c.unread_count > 0, badge: c.unread_count,
    }))
    .sort((a, b) => (b.badge || 0) - (a.badge || 0))

  const selected = conversations.find(c => c.id === selectedId)

  return <FamilyShell>
    <div className="flex items-center justify-between gap-3">
      <div><div className="eyebrow">Care team</div><h1 className="font-display text-3xl font-bold text-kGreen">Messages</h1></div>
      <button onClick={() => setComposing(true)} className="btn-orange"><MessageSquarePlus size={16} /> New message</button>
    </div>

    <ConversationSplitView
      items={items}
      selectedKey={selectedId}
      onSelect={setSelectedId}
      loading={loading}
      error={error}
      onRetry={load}
      search={{ value: search, onChange: setSearch }}
      emptyMessage="No conversations yet — start one with the care team above."
    >
      {selected && <DirectConversationThread conversationId={selected.id} otherUser={selected.other_user} onRead={load} />}
    </ConversationSplitView>

    {composing && <ComposeMessageModal onClose={() => setComposing(false)} onSent={load} showToast={showToast} />}
  </FamilyShell>
}
