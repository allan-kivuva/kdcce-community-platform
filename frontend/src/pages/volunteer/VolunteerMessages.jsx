import { useState, useEffect, useCallback } from 'react'
import { HandHeart, Home, MessageSquarePlus, User } from 'lucide-react'
import VolunteerShell from '../../components/volunteer/VolunteerShell'
import ConversationSplitView from '../../components/admin/ConversationSplitView'
import DirectConversationThread from '../../components/admin/DirectConversationThread'
import AssignmentConversation from '../../components/admin/AssignmentConversation'
import ComposeMessageModal from '../../components/admin/ComposeMessageModal'
import { timeAgo, errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch } from '../../lib/api'
import { useVolunteerData } from '../../lib/VolunteerDataContext'

const KIND_ICON = { direct: <User size={18} />, 'Home Visit': <Home size={16} />, 'Assistance Request': <HandHeart size={16} /> }

// The general direct-message inbox (new in this phase) plus this
// volunteer's own per-assignment threads (unchanged — same
// AssignmentConversation component, same access rules, just presented
// in the same modern split-pane list as everything else here).
export default function VolunteerMessages({ showToast }) {
  const { visits, requests, loading: assignmentsLoading, error: assignmentsError, reload } = useVolunteerData()
  const [direct, setDirect] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedKey, setSelectedKey] = useState(null)
  const [search, setSearch] = useState('')
  const [composing, setComposing] = useState(false)

  const loadDirect = useCallback(async () => {
    setLoading(true)
    setError('')
    try { setDirect((await apiFetch('/api/messages/conversations')).conversations) }
    catch (err) { setError(errorMessage(err)) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { loadDirect() }, [loadDirect])

  const assignments = [
    ...visits.map(x => ({ kind: 'Home Visit', basePath: `/api/home-visits/${x.id}`, id: x.id, name: x.elderly_member_name, status: x.status })),
    ...requests.map(x => ({ kind: 'Assistance Request', basePath: `/api/assistance-requests/${x.id}`, id: x.id, name: x.elderly_member_name, status: x.status })),
  ]

  const items = [
    ...direct.map(c => ({
      key: `direct-${c.id}`, id: c.id, kind: 'direct', icon: KIND_ICON.direct,
      title: c.other_user.name, subtitle: c.other_user.role,
      preview: c.last_message?.body, timestamp: timeAgo(c.updated_at), updatedAt: c.updated_at,
      unread: c.unread_count > 0, badge: c.unread_count,
    })),
    ...assignments.map(a => ({
      key: `assign-${a.kind}-${a.id}`, ...a, icon: KIND_ICON[a.kind],
      title: `${a.kind} — ${a.name}`, subtitle: a.status, preview: null, timestamp: '', updatedAt: '1970-01-01',
      unread: false,
    })),
  ].filter(it => !search || it.title.toLowerCase().includes(search.toLowerCase()))
   .sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt))

  const selected = items.find(it => it.key === selectedKey)

  function selectAndClearUnread(key) {
    setSelectedKey(key)
    if (key) setDirect(prev => prev.map(c => `direct-${c.id}` === key ? { ...c, unread_count: 0 } : c))
  }

  return <VolunteerShell>
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div><div className="eyebrow">Communication</div><h1 className="font-display text-3xl font-bold text-kGreen">Messages</h1></div>
      <button onClick={() => setComposing(true)} className="btn-orange"><MessageSquarePlus size={16} /> New message</button>
    </div>
    <p className="mt-2 text-sm text-kMuted">Message admin/staff directly, or continue the conversation on any of your assignments.</p>

    <ConversationSplitView
      items={items} selectedKey={selectedKey} onSelect={selectAndClearUnread}
      loading={loading || assignmentsLoading} error={error || assignmentsError} onRetry={() => { loadDirect(); reload() }}
      search={{ value: search, onChange: setSearch }}
      emptyMessage="No conversations yet — message staff or check back once you have an assignment."
    >
      {selected?.kind === 'direct' && <DirectConversationThread conversationId={selected.id} otherUser={{ name: selected.title, role: selected.subtitle }} onRead={loadDirect} />}
      {selected && selected.kind !== 'direct' && <div className="flex-1 overflow-y-auto p-4">
        <div className="mb-3"><div className="text-sm font-bold text-kInk">{selected.title}</div><div className="text-xs text-kMuted">{selected.subtitle}</div></div>
        <AssignmentConversation basePath={selected.basePath} />
      </div>}
    </ConversationSplitView>

    {composing && <ComposeMessageModal onClose={() => setComposing(false)} onSent={loadDirect} showToast={showToast} />}
  </VolunteerShell>
}
