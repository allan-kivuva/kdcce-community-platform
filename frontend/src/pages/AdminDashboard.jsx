import { useState } from 'react'
import { Routes, Route, Link } from 'react-router-dom'
import { BarChart3, Search, Plus, Trash2, Pencil, Download, ChevronDown, Mail, MailOpen, Reply, Settings } from 'lucide-react'
import Modal from '../components/admin/Modal'
import Toast from '../components/admin/Toast'
import Shell from '../components/admin/Shell'
import { useToast, errorMessage, LoadingState, ErrorState } from '../components/admin/adminHelpers'
import { downloadFile } from '../lib/api'
import { useApiResource } from '../lib/useApiResource'
import ElderlyManager from './admin/ElderlyManager'
import AttendanceManager from './admin/AttendanceManager'

// Inbox has no backend yet (Step 3+) — still mock, unchanged from before.
const initialInbox = [
  { id: 1, name: 'Grace M.', email: 'grace@example.com', subject: 'Volunteering interest', message: 'Hi, I would love to volunteer on weekends. What is the best way to get started?', date: '2026-08-19', read: false },
  { id: 2, name: 'Daniel K.', email: 'daniel@example.com', subject: 'Partnership proposal', message: 'Our company would like to explore a partnership for the feeding program.', date: '2026-08-17', read: true },
  { id: 3, name: 'Faith W.', email: 'faith@example.com', subject: 'Thank you', message: 'Thank you for the wonderful work you do for our elders in Kibera.', date: '2026-08-15', read: true }
]

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

function DonationsManager({ donations, loading, error, reload, patchDonation, addDonation, showToast }) {
  const [q, setQ] = useState('')
  const [statusFilter, setStatusFilter] = useState('All')
  const [modal, setModal] = useState(null)
  const [saving, setSaving] = useState(false)
  const filtered = donations.filter(d => (statusFilter === 'All' || d.status === statusFilter) && (d.donor_name.toLowerCase().includes(q.toLowerCase()) || d.donor_email.toLowerCase().includes(q.toLowerCase())))

  async function save(e) {
    e.preventDefault()
    const f = new FormData(e.target)
    setSaving(true)
    try {
      if (modal.data) {
        await patchDonation(modal.data.id, {
          donor_name: f.get('donor'), donor_email: f.get('email'),
          amount: Number(f.get('amount')), frequency: f.get('frequency'), status: f.get('status')
        })
        showToast('Donation updated')
      } else {
        await addDonation({
          donor_name: f.get('donor'), donor_email: f.get('email'),
          amount: Number(f.get('amount')), frequency: f.get('frequency')
        })
        showToast('Donation added')
      }
      setModal(null)
    } catch (err) {
      showToast(errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  async function downloadCsvExport() {
    try { await downloadFile('/api/donations/export.csv', 'donations.csv') }
    catch (err) { showToast(errorMessage(err)) }
  }

  return <Shell>
    <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center"><div><div className="eyebrow">Manage</div><h1 className="font-display text-3xl font-bold text-kGreen">Donations manager</h1></div><div className="flex gap-2"><button onClick={() => setModal({})} className="btn-green"><Plus size={16} /> Add new</button><button onClick={downloadCsvExport} className="btn-orange"><Download size={16} /> CSV</button></div></div>
    {loading ? <LoadingState label="donations" /> : error ? <ErrorState message={error} onRetry={reload} /> : <div className="card-k mt-7 overflow-hidden">
      <div className="flex flex-col gap-3 border-b border-kBorderSoft p-5 sm:flex-row"><div className="relative flex-1"><Search className="absolute left-3 top-3.5 text-kMuted" size={17} /><input value={q} onChange={e => setQ(e.target.value)} className="input-k pl-10" placeholder="Search donor or email..." /></div><select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="rounded-xl border border-kBorder bg-kSurface px-4 py-3 text-sm text-kInk"><option>All</option><option>Paid</option><option>Pending</option></select></div>
      <div className="overflow-x-auto"><table className="w-full min-w-[700px] text-left text-sm"><thead className="bg-kBorderSoft text-xs uppercase tracking-wider text-kMuted"><tr><th className="px-5 py-4">Donor</th><th className="px-5 py-4">Email</th><th className="px-5 py-4">Amount</th><th className="px-5 py-4">Frequency</th><th className="px-5 py-4">Status</th><th className="px-5 py-4">Actions</th></tr></thead><tbody>
        {filtered.map(d => <tr key={d.id} className="border-b border-kBorderSoft"><td className="px-5 py-4 font-semibold text-kInk">{d.donor_name}</td><td className="px-5 py-4 text-kMuted">{d.donor_email}</td><td className="px-5 py-4 text-kMuted">KES {Number(d.amount).toLocaleString()}</td><td className="px-5 py-4 text-kMuted">{frequencyLabel(d.frequency)}</td><td className="px-5 py-4 text-kMuted">{d.status}</td><td className="px-5 py-4"><button onClick={() => setModal({ data: d })} className="text-kOrange"><Pencil size={16} /></button></td></tr>)}
        {filtered.length === 0 && <tr><td colSpan={6} className="px-5 py-10 text-center text-sm text-kMuted">No donations match your search.</td></tr>}
      </tbody></table></div>
    </div>}
    {modal && <Modal title={modal.data ? 'Edit donation' : 'Add donation'} onClose={() => setModal(null)}>
      <form onSubmit={save} className="grid gap-4">
        <label className="text-sm font-semibold">Donor name<input name="donor" defaultValue={modal.data?.donor_name} className="input-k mt-2" required /></label>
        <label className="text-sm font-semibold">Email<input name="email" type="email" defaultValue={modal.data?.donor_email} className="input-k mt-2" required /></label>
        <label className="text-sm font-semibold">Amount (KES)<input name="amount" type="number" min="1" defaultValue={modal.data?.amount} className="input-k mt-2" required /></label>
        <label className="text-sm font-semibold">Frequency<select name="frequency" defaultValue={modal.data?.frequency || 'one-time'} className="input-k mt-2"><option value="one-time">One-time</option><option value="monthly">Monthly</option></select></label>
        <label className="text-sm font-semibold">Status<select name="status" defaultValue={modal.data?.status || 'Paid'} className="input-k mt-2"><option>Paid</option><option>Pending</option></select></label>
        <button disabled={saving} className="btn-orange mt-2 disabled:opacity-60">{saving ? 'Saving…' : modal.data ? 'Save changes' : 'Add donation'}</button>
      </form>
    </Modal>}
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

function InboxManager({ messages, setMessages, showToast }) {
  const [openId, setOpenId] = useState(null)
  function toggleRead(m) { setMessages(ms => ms.map(x => x.id === m.id ? { ...x, read: !x.read } : x)); showToast(m.read ? 'Marked as unread' : 'Marked as read') }
  function remove(m) { if (window.confirm(`Delete message from ${m.name}?`)) { setMessages(ms => ms.filter(x => x.id !== m.id)); showToast('Message deleted') } }
  const unread = messages.filter(m => !m.read).length

  return <Shell>
    <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center"><div><div className="eyebrow">Manage</div><h1 className="font-display text-3xl font-bold text-kGreen">Inbox</h1></div><div className="rounded-full bg-kTint px-4 py-2 text-sm font-bold text-kOrange">{unread} unread</div></div>
    <div className="card-k mt-7 divide-y divide-kBorderSoft">
      {messages.map(m => <div key={m.id} className="p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <button onClick={() => setOpenId(id => id === m.id ? null : m.id)} className="flex flex-1 items-center gap-3 text-left">
            {m.read ? <MailOpen size={18} className="text-kMuted" /> : <Mail size={18} className="text-kOrange" />}
            <div><div className={`text-sm ${m.read ? 'font-semibold text-kInk' : 'font-bold text-kGreen'}`}>{m.name} &middot; {m.subject}</div><div className="text-xs text-kMuted">{m.email} &middot; {m.date}</div></div>
          </button>
          <div className="flex gap-3 text-xs font-semibold"><button onClick={() => toggleRead(m)} className="text-kOrange">{m.read ? 'Mark unread' : 'Mark read'}</button><button onClick={() => remove(m)} className="text-kMuted hover:text-red-600"><Trash2 size={16} /></button></div>
        </div>
        {openId === m.id && <div className="mt-4 rounded-xl bg-kCream p-4 text-sm leading-6 text-kInk">{m.message}<div className="mt-3"><a href={`mailto:${m.email}`} className="inline-flex items-center gap-2 text-sm font-semibold text-kOrange"><Reply size={14} /> Reply by email</a></div></div>}
      </div>)}
      {messages.length === 0 && <p className="p-5 text-sm text-kMuted">No messages.</p>}
    </div>
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
  const [inbox, setInbox] = useState(initialInbox)
  const [toast, showToast] = useToast()

  return <>
    <Routes>
      <Route index element={<Overview donations={donationsApi.items} blogPosts={blogApi.items} crafts={craftsApi.items} />} />
      <Route path="elderly" element={<ElderlyManager showToast={showToast} />} />
      <Route path="attendance" element={<AttendanceManager showToast={showToast} />} />
      <Route path="donations" element={<DonationsManager
        donations={donationsApi.items} loading={donationsApi.loading} error={donationsApi.error} reload={donationsApi.reload}
        addDonation={body => donationsApi.create(body, '/api/donations')}
        patchDonation={(id, body) => donationsApi.patch(id, body, '/api/donations')}
        showToast={showToast} />} />
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
      <Route path="inbox" element={<InboxManager messages={inbox} setMessages={setInbox} showToast={showToast} />} />
      <Route path="settings" element={<SettingsPage showToast={showToast} />} />
    </Routes>
    <Toast message={toast} />
  </>
}
