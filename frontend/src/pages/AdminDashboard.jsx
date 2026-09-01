import { useState } from 'react'
import { Routes, Route } from 'react-router-dom'
import { Search, Plus, Trash2, Pencil, Settings } from 'lucide-react'
import Modal from '../components/admin/Modal'
import Toast from '../components/admin/Toast'
import Shell from '../components/admin/Shell'
import { useToast, errorMessage, LoadingState, ErrorState } from '../components/admin/adminHelpers'
import { useApiResource } from '../lib/useApiResource'
import CommandCenter from './admin/CommandCenter'
import ElderlyManager from './admin/ElderlyManager'
import ElderlyProfile from './admin/ElderlyProfile'
import FollowUpsManager from './admin/FollowUpsManager'
import AssignmentCalendar from './admin/AssignmentCalendar'
import RecurringVisitsManager from './admin/RecurringVisitsManager'
import AttendanceManager from './admin/AttendanceManager'
import HealthManager from './admin/HealthManager'
import MedicationManager from './admin/MedicationManager'
import VolunteerManager from './admin/VolunteerManager'
import TrainingManager from './admin/TrainingManager'
import MessagesManager from './admin/MessagesManager'
import AnnouncementsManager from './admin/AnnouncementsManager'
import ProgramsManager from './admin/ProgramsManager'
import HomeVisitManager from './admin/HomeVisitManager'
import DonationsManager from './admin/DonationsManager'
import DonorsManager from './admin/DonorsManager'
import CampaignsManager from './admin/CampaignsManager'
import ExpensesManager from './admin/ExpensesManager'
import BudgetsManager from './admin/BudgetsManager'
import FinanceDashboard from './admin/FinanceDashboard'
import FeedingManager from './admin/FeedingManager'
import InventoryManager from './admin/InventoryManager'
import ActivityManager from './admin/ActivityManager'
import AssistanceManager from './admin/AssistanceManager'
import IncidentManager from './admin/IncidentManager'
import ReportsManager from './admin/ReportsManager'
import AnalyticsManager from './admin/AnalyticsManager'
import InboxManager from './admin/InboxManager'
import UsersManager from './admin/UsersManager'
import AuditLogViewer from './admin/AuditLogViewer'
import SessionsManager from './admin/SessionsManager'
import SecurityDashboard from './admin/SecurityDashboard'
import OperationsMap from './admin/OperationsMap'
import SmartMatching from './admin/SmartMatching'
import ConsentManager from './admin/ConsentManager'
import FamilyAccessManager from './admin/FamilyAccessManager'
import ImportsManager from './admin/ImportsManager'
import AIAssistant from './admin/AIAssistant'
import AIInsights from './admin/AIInsights'

function BlogManager({ posts, loading, error, reload, addPost, patchPost, deletePost, showToast }) {
  const [q, setQ] = useState('')
  const [statusFilter, setStatusFilter] = useState('All')
  const [modal, setModal] = useState(null)
  const [saving, setSaving] = useState(false)
  const filtered = posts.filter(p => (statusFilter === 'All' || p.status === statusFilter) && p.title.toLowerCase().includes(q.toLowerCase()))

  async function save(e) {
    e.preventDefault()
    const f = new FormData(e.target)
    const data = { title: f.get('title'), type: f.get('type'), status: f.get('status') }
    setSaving(true)
    try {
      if (modal.data) { await patchPost(modal.data.id, data); showToast('Post updated') }
      else { await addPost(data); showToast('Post added') }
      setModal(null)
    } catch (err) { showToast(errorMessage(err)) }
    finally { setSaving(false) }
  }
  async function remove(p) {
    if (!window.confirm(`Delete "${p.title}"?`)) return
    try { await deletePost(p.id); showToast('Post deleted') }
    catch (err) { showToast(errorMessage(err)) }
  }

  return <Shell>
    <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center"><div><div className="eyebrow">Manage</div><h1 className="font-display text-3xl font-bold text-kGreen">Blog posts</h1></div><button onClick={() => setModal({})} className="btn-green"><Plus size={16} /> Add new</button></div>
    {loading ? <LoadingState label="posts" /> : error ? <ErrorState message={error} onRetry={reload} /> : <div className="card-k mt-7 overflow-hidden">
      <div className="flex flex-col gap-3 border-b border-kBorderSoft p-5 sm:flex-row"><div className="relative flex-1"><Search className="absolute left-3 top-3.5 text-kMuted" size={17} /><input value={q} onChange={e => setQ(e.target.value)} className="input-k pl-10" placeholder="Search title..." /></div><select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="rounded-xl border border-kBorder bg-kSurface px-4 py-3 text-sm text-kInk"><option>All</option><option>Published</option><option>Draft</option></select></div>
      <div className="overflow-x-auto"><table className="w-full min-w-[700px] text-left text-sm"><thead className="bg-kBorderSoft text-xs uppercase tracking-wider text-kMuted"><tr><th className="px-5 py-4">Title</th><th className="px-5 py-4">Type</th><th className="px-5 py-4">Status</th><th className="px-5 py-4">Actions</th></tr></thead><tbody>
        {filtered.map(p => <tr key={p.id} className="border-b border-kBorderSoft"><td className="px-5 py-4 font-semibold text-kInk">{p.title}</td><td className="px-5 py-4 text-kMuted">{p.type}</td><td className="px-5 py-4 text-kMuted">{p.status}</td><td className="px-5 py-4"><div className="flex gap-3"><button onClick={() => setModal({ data: p })} className="text-kOrange"><Pencil size={16} /></button><button onClick={() => remove(p)} className="text-kMuted hover:text-red-600"><Trash2 size={16} /></button></div></td></tr>)}
        {filtered.length === 0 && <tr><td colSpan={4} className="px-5 py-10 text-center text-sm text-kMuted">No posts match your search.</td></tr>}
      </tbody></table></div>
    </div>}
    {modal && <Modal title={modal.data ? 'Edit post' : 'Add post'} onClose={() => setModal(null)}>
      <form onSubmit={save} className="grid gap-4">
        <label className="text-sm font-semibold">Title<input name="title" defaultValue={modal.data?.title} className="input-k mt-2" required /></label>
        <label className="text-sm font-semibold">Type<select name="type" defaultValue={modal.data?.type || 'Story'} className="input-k mt-2"><option>Story</option><option>Skills</option><option>Update</option></select></label>
        <label className="text-sm font-semibold">Status<select name="status" defaultValue={modal.data?.status || 'Draft'} className="input-k mt-2"><option>Published</option><option>Draft</option></select></label>
        <button disabled={saving} className="btn-orange mt-2 disabled:opacity-60">{saving ? 'Saving…' : modal.data ? 'Save changes' : 'Add post'}</button>
      </form>
    </Modal>}
  </Shell>
}

function GalleryManager({ images, loading, error, reload, addImage, deleteImage, showToast }) {
  const [modal, setModal] = useState(null)
  const [saving, setSaving] = useState(false)
  async function save(e) {
    e.preventDefault()
    const url = new FormData(e.target).get('url')
    setSaving(true)
    try { await addImage({ url }); showToast('Image added'); setModal(null) }
    catch (err) { showToast(errorMessage(err)) }
    finally { setSaving(false) }
  }
  async function remove(img) {
    if (!window.confirm('Remove this image?')) return
    try { await deleteImage(img.id); showToast('Image removed') }
    catch (err) { showToast(errorMessage(err)) }
  }

  return <Shell>
    <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center"><div><div className="eyebrow">Manage</div><h1 className="font-display text-3xl font-bold text-kGreen">Gallery manager</h1></div><button onClick={() => setModal({})} className="btn-orange"><Plus size={16} /> Add image</button></div>
    {loading ? <LoadingState label="images" /> : error ? <ErrorState message={error} onRetry={reload} /> : <div className="mt-7 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">{images.map(img => <div key={img.id} className="group relative overflow-hidden rounded-2xl"><img src={img.url} alt="" className="h-48 w-full object-cover" /><button onClick={() => remove(img)} className="absolute right-3 top-3 grid h-9 w-9 place-items-center rounded-full bg-black/60 text-white opacity-0 transition group-hover:opacity-100"><Trash2 size={16} /></button></div>)}
      {images.length === 0 && <p className="text-sm text-kMuted">No images yet — add one to get started.</p>}
    </div>}
    {modal && <Modal title="Add image" onClose={() => setModal(null)}>
      <form onSubmit={save} className="grid gap-4">
        <label className="text-sm font-semibold">Image URL<input name="url" className="input-k mt-2" placeholder="/images/example.jpg" required /></label>
        <button disabled={saving} className="btn-orange mt-2 disabled:opacity-60">{saving ? 'Adding…' : 'Add image'}</button>
      </form>
    </Modal>}
  </Shell>
}

function TeamManager({ team, loading, error, reload, addMember, patchMember, deleteMember, showToast }) {
  const [modal, setModal] = useState(null)
  const [saving, setSaving] = useState(false)
  async function save(e) {
    e.preventDefault()
    const f = new FormData(e.target)
    const data = { name: f.get('name'), role: f.get('role'), image: f.get('image') }
    setSaving(true)
    try {
      if (modal.data) { await patchMember(modal.data.id, data); showToast('Team member updated') }
      else { await addMember(data); showToast('Team member added') }
      setModal(null)
    } catch (err) { showToast(errorMessage(err)) }
    finally { setSaving(false) }
  }
  async function remove(t) {
    if (!window.confirm(`Remove ${t.name} from the team?`)) return
    try { await deleteMember(t.id); showToast('Team member removed') }
    catch (err) { showToast(errorMessage(err)) }
  }

  return <Shell>
    <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center"><div><div className="eyebrow">Manage</div><h1 className="font-display text-3xl font-bold text-kGreen">Team manager</h1></div><button onClick={() => setModal({})} className="btn-orange"><Plus size={16} /> Add team member</button></div>
    {loading ? <LoadingState label="team" /> : error ? <ErrorState message={error} onRetry={reload} /> : <div className="mt-7 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">{team.map(t => <div key={t.id} className="card-k overflow-hidden"><img src={t.image} alt={t.name} className="h-44 w-full object-cover" /><div className="p-5"><h3 className="font-display text-lg font-semibold text-kGreen">{t.name}</h3><p className="mt-1 text-sm text-kMuted">{t.role}</p><div className="mt-4 flex gap-3"><button onClick={() => setModal({ data: t })} className="text-sm font-semibold text-kOrange">Edit</button><button onClick={() => remove(t)} className="text-sm font-semibold text-kMuted hover:text-red-600">Remove</button></div></div></div>)}
    </div>}
    {modal && <Modal title={modal.data ? 'Edit team member' : 'Add team member'} onClose={() => setModal(null)}>
      <form onSubmit={save} className="grid gap-4">
        <label className="text-sm font-semibold">Name<input name="name" defaultValue={modal.data?.name} className="input-k mt-2" required /></label>
        <label className="text-sm font-semibold">Role<input name="role" defaultValue={modal.data?.role} className="input-k mt-2" required /></label>
        <label className="text-sm font-semibold">Photo URL<input name="image" defaultValue={modal.data?.image} className="input-k mt-2" placeholder="/images/example.jpg" required /></label>
        <button disabled={saving} className="btn-orange mt-2 disabled:opacity-60">{saving ? 'Saving…' : modal.data ? 'Save changes' : 'Add team member'}</button>
      </form>
    </Modal>}
  </Shell>
}

function CraftsManager({ crafts, loading, error, reload, addCraft, patchCraft, deleteCraft, showToast }) {
  const [modal, setModal] = useState(null)
  const [saving, setSaving] = useState(false)
  async function save(e) {
    e.preventDefault()
    const f = new FormData(e.target)
    const data = { title: f.get('title'), category: f.get('category'), maker: f.get('maker'), price: Number(f.get('price')), status: f.get('status') }
    setSaving(true)
    try {
      if (modal.data) { await patchCraft(modal.data.id, data); showToast('Craft item updated') }
      else { await addCraft(data); showToast('Craft item added') }
      setModal(null)
    } catch (err) { showToast(errorMessage(err)) }
    finally { setSaving(false) }
  }
  async function remove(c) {
    if (!window.confirm(`Delete "${c.title}"?`)) return
    try { await deleteCraft(c.id); showToast('Craft item deleted') }
    catch (err) { showToast(errorMessage(err)) }
  }

  return <Shell>
    <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center"><div><div className="eyebrow">Manage</div><h1 className="font-display text-3xl font-bold text-kGreen">Craft shop manager</h1></div><button onClick={() => setModal({})} className="btn-orange"><Plus size={16} /> Add craft item</button></div>
    {loading ? <LoadingState label="craft items" /> : error ? <ErrorState message={error} onRetry={reload} /> : <div className="card-k mt-7 overflow-hidden"><div className="overflow-x-auto"><table className="w-full min-w-[700px] text-left text-sm"><thead className="bg-kBorderSoft text-xs uppercase tracking-wider text-kMuted"><tr><th className="px-5 py-4">Title</th><th className="px-5 py-4">Category</th><th className="px-5 py-4">Maker</th><th className="px-5 py-4">Price</th><th className="px-5 py-4">Status</th><th className="px-5 py-4">Actions</th></tr></thead><tbody>
      {crafts.map(c => <tr key={c.id} className="border-b border-kBorderSoft"><td className="px-5 py-4 font-semibold text-kInk">{c.title}</td><td className="px-5 py-4 text-kMuted">{c.category}</td><td className="px-5 py-4 text-kMuted">{c.maker}</td><td className="px-5 py-4 text-kMuted">KES {Number(c.price).toLocaleString()}</td><td className="px-5 py-4 text-kMuted">{c.status}</td><td className="px-5 py-4"><div className="flex gap-3"><button onClick={() => setModal({ data: c })} className="text-kOrange"><Pencil size={16} /></button><button onClick={() => remove(c)} className="text-kMuted hover:text-red-600"><Trash2 size={16} /></button></div></td></tr>)}
    </tbody></table></div></div>}
    {modal && <Modal title={modal.data ? 'Edit craft item' : 'Add craft item'} onClose={() => setModal(null)}>
      <form onSubmit={save} className="grid gap-4">
        <label className="text-sm font-semibold">Title<input name="title" defaultValue={modal.data?.title} className="input-k mt-2" required /></label>
        <label className="text-sm font-semibold">Category<select name="category" defaultValue={modal.data?.category || 'Beadwork'} className="input-k mt-2"><option>Beadwork</option><option>Knitting</option><option>Other</option></select></label>
        <label className="text-sm font-semibold">Maker<input name="maker" defaultValue={modal.data?.maker} className="input-k mt-2" required /></label>
        <label className="text-sm font-semibold">Price (KES)<input name="price" type="number" min="1" defaultValue={modal.data?.price} className="input-k mt-2" required /></label>
        <label className="text-sm font-semibold">Status<select name="status" defaultValue={modal.data?.status || 'Available'} className="input-k mt-2"><option>Available</option><option>Reserved</option><option>Sold</option></select></label>
        <button disabled={saving} className="btn-orange mt-2 disabled:opacity-60">{saving ? 'Saving…' : modal.data ? 'Save changes' : 'Add craft item'}</button>
      </form>
    </Modal>}
  </Shell>
}

function SettingsPage({ showToast }) {
  const [emailAlerts, setEmailAlerts] = useState(true)
  const [weeklyDigest, setWeeklyDigest] = useState(false)
  return <Shell><div className="card-k p-8">
    <div className="flex items-center gap-3 text-kGreen"><Settings /><h2 className="font-display text-2xl font-bold">Settings</h2></div>
    <form onSubmit={e => { e.preventDefault(); showToast('Settings saved') }} className="mt-6 grid gap-5 max-w-md">
      <label className="flex items-center justify-between rounded-xl border border-kBorder p-4 text-sm font-semibold"><span>Email me for new donations</span><input type="checkbox" checked={emailAlerts} onChange={e => setEmailAlerts(e.target.checked)} className="h-5 w-5" /></label>
      <label className="flex items-center justify-between rounded-xl border border-kBorder p-4 text-sm font-semibold"><span>Weekly digest email</span><input type="checkbox" checked={weeklyDigest} onChange={e => setWeeklyDigest(e.target.checked)} className="h-5 w-5" /></label>
      <button className="btn-orange w-fit">Save changes</button>
    </form>
  </div></Shell>
}

export default function AdminDashboard() {
  const blogApi = useApiResource('/api/admin/blog', { listKey: 'posts', itemKey: 'post' })
  const galleryApi = useApiResource('/api/gallery', { listKey: 'images', itemKey: 'image' })
  const teamApi = useApiResource('/api/team', { listKey: 'team', itemKey: 'member' })
  const craftsApi = useApiResource('/api/crafts', { listKey: 'crafts', itemKey: 'craft' })
  const [toast, showToast] = useToast()

  return <>
    <Routes>
      <Route index element={<CommandCenter showToast={showToast} />} />
      <Route path="elderly" element={<ElderlyManager showToast={showToast} />} />
      <Route path="elderly/:id" element={<ElderlyProfile />} />
      <Route path="followups" element={<FollowUpsManager showToast={showToast} />} />
      <Route path="calendar" element={<AssignmentCalendar />} />
      <Route path="attendance" element={<AttendanceManager showToast={showToast} />} />
      <Route path="health" element={<HealthManager showToast={showToast} />} />
      <Route path="medication" element={<MedicationManager showToast={showToast} />} />
      <Route path="volunteers" element={<VolunteerManager showToast={showToast} />} />
      <Route path="home-visits" element={<HomeVisitManager showToast={showToast} />} />
      <Route path="recurring-visits" element={<RecurringVisitsManager showToast={showToast} />} />
      <Route path="training" element={<TrainingManager showToast={showToast} />} />
      <Route path="messages" element={<MessagesManager showToast={showToast} />} />
      <Route path="announcements" element={<AnnouncementsManager showToast={showToast} />} />
      <Route path="programs" element={<ProgramsManager showToast={showToast} />} />
      <Route path="donations" element={<DonationsManager showToast={showToast} />} />
      <Route path="donors" element={<DonorsManager showToast={showToast} />} />
      <Route path="campaigns" element={<CampaignsManager showToast={showToast} />} />
      <Route path="expenses" element={<ExpensesManager showToast={showToast} />} />
      <Route path="budgets" element={<BudgetsManager showToast={showToast} />} />
      <Route path="finance" element={<FinanceDashboard />} />
      <Route path="feeding" element={<FeedingManager showToast={showToast} />} />
      <Route path="inventory" element={<InventoryManager showToast={showToast} />} />
      <Route path="activities" element={<ActivityManager showToast={showToast} />} />
      <Route path="assistance" element={<AssistanceManager showToast={showToast} />} />
      <Route path="incidents" element={<IncidentManager showToast={showToast} />} />
      <Route path="reports" element={<ReportsManager showToast={showToast} />} />
      <Route path="analytics" element={<AnalyticsManager />} />
      <Route path="blog" element={<BlogManager
        posts={blogApi.items} loading={blogApi.loading} error={blogApi.error} reload={blogApi.reload}
        addPost={blogApi.create} patchPost={blogApi.patch} deletePost={blogApi.remove} showToast={showToast} />} />
      <Route path="gallery" element={<GalleryManager
        images={galleryApi.items} loading={galleryApi.loading} error={galleryApi.error} reload={galleryApi.reload}
        addImage={body => galleryApi.create(body, '/api/admin/gallery')}
        deleteImage={id => galleryApi.remove(id, '/api/admin/gallery')}
        showToast={showToast} />} />
      <Route path="team" element={<TeamManager
        team={teamApi.items} loading={teamApi.loading} error={teamApi.error} reload={teamApi.reload}
        addMember={body => teamApi.create(body, '/api/admin/team')}
        patchMember={(id, body) => teamApi.patch(id, body, '/api/admin/team')}
        deleteMember={id => teamApi.remove(id, '/api/admin/team')}
        showToast={showToast} />} />
      <Route path="crafts" element={<CraftsManager
        crafts={craftsApi.items} loading={craftsApi.loading} error={craftsApi.error} reload={craftsApi.reload}
        addCraft={body => craftsApi.create(body, '/api/admin/crafts')}
        patchCraft={(id, body) => craftsApi.patch(id, body, '/api/admin/crafts')}
        deleteCraft={id => craftsApi.remove(id, '/api/admin/crafts')}
        showToast={showToast} />} />
      <Route path="inbox" element={<InboxManager showToast={showToast} />} />
      <Route path="users" element={<UsersManager showToast={showToast} />} />
      <Route path="audit-logs" element={<AuditLogViewer showToast={showToast} />} />
      <Route path="sessions" element={<SessionsManager showToast={showToast} />} />
      <Route path="security" element={<SecurityDashboard showToast={showToast} />} />
      <Route path="operations-map" element={<OperationsMap />} />
      <Route path="matching" element={<SmartMatching showToast={showToast} />} />
      <Route path="consents" element={<ConsentManager showToast={showToast} />} />
      <Route path="family-access" element={<FamilyAccessManager showToast={showToast} />} />
      <Route path="imports" element={<ImportsManager showToast={showToast} />} />
      <Route path="ai-assistant" element={<AIAssistant showToast={showToast} />} />
      <Route path="ai-insights" element={<AIInsights showToast={showToast} />} />
      <Route path="settings" element={<SettingsPage showToast={showToast} />} />
    </Routes>
    <Toast message={toast} />
  </>
}
