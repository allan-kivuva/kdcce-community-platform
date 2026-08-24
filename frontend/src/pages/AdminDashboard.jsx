import { useState } from 'react'
import { Routes, Route, Link } from 'react-router-dom'
import { BarChart3, Search, Plus, Trash2, Pencil, ChevronDown, Settings } from 'lucide-react'
import Modal from '../components/admin/Modal'
import Toast from '../components/admin/Toast'
import Shell from '../components/admin/Shell'
import { useToast, errorMessage, LoadingState, ErrorState } from '../components/admin/adminHelpers'
import { useApiResource } from '../lib/useApiResource'
import ElderlyManager from './admin/ElderlyManager'
import ElderlyProfile from './admin/ElderlyProfile'
import FollowUpsManager from './admin/FollowUpsManager'
import AssignmentCalendar from './admin/AssignmentCalendar'
import AttendanceManager from './admin/AttendanceManager'
import HealthManager from './admin/HealthManager'
import MedicationManager from './admin/MedicationManager'
import VolunteerManager from './admin/VolunteerManager'
import HomeVisitManager from './admin/HomeVisitManager'
import DonationsManager from './admin/DonationsManager'
import FeedingManager from './admin/FeedingManager'
import InventoryManager from './admin/InventoryManager'
import ActivityManager from './admin/ActivityManager'
import AssistanceManager from './admin/AssistanceManager'
import IncidentManager from './admin/IncidentManager'
import ReportsManager from './admin/ReportsManager'
import AnalyticsManager from './admin/AnalyticsManager'
import InboxManager from './admin/InboxManager'

function QuickActionMenu() {
  const [open, setOpen] = useState(false)
  const actions = [['Add donation', '/admin/donations'], ['New blog post', '/admin/blog'], ['Add craft item', '/admin/crafts']]
  return <div className="relative">
    <button onClick={() => setOpen(o => !o)} className="btn-orange"><Plus size={16} /> Quick action <ChevronDown size={14} /></button>
    {open && <div className="absolute right-0 z-20 mt-2 w-56 overflow-hidden rounded-xl border border-kBorderSoft bg-kSurface shadow-soft dark:shadow-none" onMouseLeave={() => setOpen(false)}>
      {actions.map(([label, to]) => <Link key={to} to={to} onClick={() => setOpen(false)} className="block px-4 py-3 text-sm font-semibold text-kGreen hover:bg-kCream">{label}</Link>)}
    </div>}
  </div>
}

function StatCard({ a, b, c }) { return <div className="card-k p-5"><div className="text-sm text-kMuted">{a}</div><div className="mt-2 font-display text-3xl font-bold text-kGreen">{b}</div><div className="mt-2 text-xs font-semibold text-kOrange">{c}</div></div> }

function frequencyLabel(freq) { return freq === 'monthly' ? 'Monthly' : 'One-time' }

function Overview({ donations, blogPosts, crafts }) {
  const total = donations.reduce((s, d) => s + Number(d.amount), 0)
  const publishedThisMonth = blogPosts.filter(p => p.status === 'Published').length
  const availableCrafts = crafts.filter(c => c.status === 'Available').length
  const stats = [['Total donations', `KES ${total.toLocaleString()}`, `${donations.length} donors`], ['This month', `KES ${total.toLocaleString()}`, `${donations.length} donors`], ['Blog posts', String(blogPosts.length), `${publishedThisMonth} published`], ['Craft items', String(crafts.length), `${availableCrafts} available now`]]
  const recent = [...donations].sort((a, b) => b.id - a.id).slice(0, 4)
  return <Shell>
    <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center"><div><div className="eyebrow">Overview</div><h1 className="font-display text-3xl font-bold text-kGreen">Good morning, staff.</h1></div><QuickActionMenu /></div>
    <div className="mt-7 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{stats.map(([a, b, c]) => <StatCard key={a} a={a} b={b} c={c} />)}</div>
    <div className="mt-6 grid gap-6 xl:grid-cols-[1.2fr_.8fr]">
      <div className="card-k p-6"><div className="flex items-center justify-between"><h2 className="font-display text-xl font-bold text-kGreen">Recent donations</h2><Link to="/admin/donations" className="text-sm font-semibold text-kOrange">View all</Link></div><div className="mt-5 overflow-x-auto"><table className="w-full min-w-[600px] text-left text-sm"><thead className="border-b border-kBorderSoft text-xs uppercase tracking-wider text-kMuted"><tr><th className="pb-3">Donor</th><th>Amount</th><th>Frequency</th><th>Status</th><th>Date</th></tr></thead><tbody>{recent.map(r => <tr key={r.id} className="border-b border-kBorderSoft"><td className="py-4 font-semibold text-kInk">{r.donor_name}</td><td className="text-kMuted">KES {Number(r.amount).toLocaleString()}</td><td className="text-kMuted">{frequencyLabel(r.frequency)}</td><td className="text-kMuted">{r.status}</td><td className="text-kMuted">{r.created_at.slice(0, 10)}</td></tr>)}</tbody></table></div></div>
      <div className="card-k p-6"><div className="flex items-center gap-3"><div className="grid h-11 w-11 place-items-center rounded-xl bg-kTint text-kOrange"><BarChart3 /></div><div><h2 className="font-display text-xl font-bold text-kGreen">Impact pulse</h2><p className="text-sm text-kMuted">Donations this week</p></div></div><div className="mt-8 flex h-36 items-end justify-between gap-3">{[42, 66, 49, 80, 58, 72, 91].map((v, i) => <div key={i} className="flex flex-1 flex-col items-center gap-2"><div className="w-full rounded-t-lg bg-kOrange/75" style={{ height: `${v}%` }} /><span className="text-[10px] text-kMuted">{['M', 'T', 'W', 'T', 'F', 'S', 'S'][i]}</span></div>)}</div></div>
    </div>
  </Shell>
}

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
  const donationsApi = useApiResource('/api/donations', { listKey: 'donations', itemKey: 'donation' })
  const blogApi = useApiResource('/api/admin/blog', { listKey: 'posts', itemKey: 'post' })
  const galleryApi = useApiResource('/api/gallery', { listKey: 'images', itemKey: 'image' })
  const teamApi = useApiResource('/api/team', { listKey: 'team', itemKey: 'member' })
  const craftsApi = useApiResource('/api/crafts', { listKey: 'crafts', itemKey: 'craft' })
  const [toast, showToast] = useToast()

  return <>
    <Routes>
      <Route index element={<Overview donations={donationsApi.items} blogPosts={blogApi.items} crafts={craftsApi.items} />} />
      <Route path="elderly" element={<ElderlyManager showToast={showToast} />} />
      <Route path="elderly/:id" element={<ElderlyProfile />} />
      <Route path="followups" element={<FollowUpsManager showToast={showToast} />} />
      <Route path="calendar" element={<AssignmentCalendar />} />
      <Route path="attendance" element={<AttendanceManager showToast={showToast} />} />
      <Route path="health" element={<HealthManager showToast={showToast} />} />
      <Route path="medication" element={<MedicationManager showToast={showToast} />} />
      <Route path="volunteers" element={<VolunteerManager showToast={showToast} />} />
      <Route path="home-visits" element={<HomeVisitManager showToast={showToast} />} />
      <Route path="donations" element={<DonationsManager showToast={showToast} />} />
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
      <Route path="settings" element={<SettingsPage showToast={showToast} />} />
    </Routes>
    <Toast message={toast} />
  </>
}
