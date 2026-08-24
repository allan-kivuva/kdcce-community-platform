import { useState } from 'react'
import { MessageSquare, Home, HandHeart } from 'lucide-react'
import VolunteerShell from '../../components/volunteer/VolunteerShell'
import Modal from '../../components/admin/Modal'
import AssignmentConversation from '../../components/admin/AssignmentConversation'
import { LoadingState, ErrorState } from '../../components/admin/adminHelpers'
import { useVolunteerData } from '../../lib/VolunteerDataContext'

const icons = { Home, HandHeart }

// Reuses the existing per-assignment AssignmentMessage thread (see
// AssignmentConversation) — this page is just an index into the
// conversations a volunteer already has, not a new messaging system.
// Authorization is unchanged: each thread is still scoped exactly like the
// assignment it belongs to, so Volunteer A can never open Volunteer B's
// thread — there is nothing here beyond what the shared portal data
// (already identity-scoped) already returns.
export default function VolunteerMessages() {
  const { visits, requests, loading, error, reload } = useVolunteerData()
  const [openThread, setOpenThread] = useState(null)

  if (loading) return <VolunteerShell><LoadingState label="messages" /></VolunteerShell>
  if (error) return <VolunteerShell><ErrorState message={error} onRetry={reload} /></VolunteerShell>

  const assignments = [
    ...visits.map(x => ({ kind: 'Home Visit', icon: 'Home', basePath: `/api/home-visits/${x.id}`, name: x.elderly_member_name, status: x.status })),
    ...requests.map(x => ({ kind: 'Assistance Request', icon: 'HandHeart', basePath: `/api/assistance-requests/${x.id}`, name: x.elderly_member_name, status: x.status })),
  ]

  return <VolunteerShell>
    <div><div className="eyebrow">Communication</div><h1 className="font-display text-3xl font-bold text-kGreen">Messages</h1></div>
    <p className="mt-2 text-sm text-kMuted">A private conversation with admin/staff for each of your assignments.</p>

    <div className="mt-7 grid gap-3">
      {assignments.map(a => { const Icon = icons[a.icon]; return <button key={a.basePath} onClick={() => setOpenThread(a)} className="card-k flex items-center justify-between gap-3 p-4 text-left hover:border-kOrange">
        <div className="flex items-center gap-3"><div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-kTint text-kOrange"><Icon size={17} /></div><div><div className="text-sm font-semibold text-kInk">{a.kind} — {a.name}</div><div className="text-xs text-kMuted">{a.status}</div></div></div>
        <MessageSquare size={16} className="shrink-0 text-kOrange" />
      </button> })}
      {assignments.length === 0 && <div className="card-k p-10 text-center text-sm text-kMuted">No assignments yet — conversations appear here once you have one.</div>}
    </div>

    {openThread && <Modal title={`${openThread.kind} — ${openThread.name}`} onClose={() => setOpenThread(null)}>
      <AssignmentConversation basePath={openThread.basePath} />
    </Modal>}
  </VolunteerShell>
}
