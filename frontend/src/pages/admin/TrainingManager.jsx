import { useState, useEffect } from 'react'
import { GraduationCap, Plus, Users } from 'lucide-react'
import Shell from '../../components/admin/Shell'
import Modal from '../../components/admin/Modal'
import StatusBadge from '../../components/admin/StatusBadge'
import { LoadingState, ErrorState, EmptyState, errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch } from '../../lib/api'
import { useApiResource } from '../../lib/useApiResource'

function CourseFormModal({ onClose, onSaved, showToast }) {
  const [saving, setSaving] = useState(false)

  async function submit(e) {
    e.preventDefault()
    const f = new FormData(e.target)
    setSaving(true)
    try {
      await apiFetch('/api/training', {
        method: 'POST',
        body: {
          title: f.get('title'),
          description: f.get('description') || null,
          estimated_minutes: f.get('estimated_minutes') ? Number(f.get('estimated_minutes')) : null,
          required: f.get('required') === 'on',
        },
      })
      showToast('Course created')
      onSaved()
      onClose()
    } catch (err) { showToast(errorMessage(err)) }
    finally { setSaving(false) }
  }

  return <Modal title="New training course" onClose={onClose}>
    <form onSubmit={submit} className="grid gap-3">
      <label className="text-sm font-semibold">Title<input name="title" required className="input-k mt-1" /></label>
      <label className="text-sm font-semibold">Description<textarea name="description" rows={3} className="input-k mt-1" /></label>
      <label className="text-sm font-semibold">Estimated minutes<input name="estimated_minutes" type="number" min="0" className="input-k mt-1" /></label>
      <label className="flex items-center gap-2 text-sm font-semibold"><input name="required" type="checkbox" className="h-4 w-4" /> Required for all volunteers</label>
      <button disabled={saving} className="btn-orange mt-2 justify-center disabled:opacity-60">{saving ? 'Creating…' : 'Create course'}</button>
    </form>
  </Modal>
}

function CompletionsModal({ course, onClose, showToast }) {
  const [completions, setCompletions] = useState(null)
  useEffect(() => {
    apiFetch(`/api/training/${course.id}/completions`).then(d => setCompletions(d.completions)).catch(err => showToast(errorMessage(err)))
  }, [course.id, showToast])
  return <Modal title={`${course.title} — progress`} onClose={onClose}>
    {!completions ? <p className="text-sm text-kMuted">Loading…</p> : <div className="grid gap-2">
      {completions.map(c => <div key={c.volunteer_profile_id} className="flex items-center justify-between rounded-xl bg-kCream px-3 py-2 text-sm">
        <span className="font-semibold text-kInk">{c.volunteer_name}</span>
        <StatusBadge value={c.status} />
      </div>)}
      {completions.length === 0 && <p className="text-sm text-kMuted">No volunteers have started this course yet.</p>}
    </div>}
  </Modal>
}

export default function TrainingManager({ showToast }) {
  const coursesApi = useApiResource('/api/training?include_inactive=true', { listKey: 'courses', itemKey: 'course' })
  const [creating, setCreating] = useState(false)
  const [viewingCompletions, setViewingCompletions] = useState(null)

  async function toggleActive(course) {
    try { await coursesApi.patch(course.id, { active: !course.active }, '/api/training'); showToast(course.active ? 'Course deactivated' : 'Course reactivated') }
    catch (err) { showToast(errorMessage(err)) }
  }

  return <Shell>
    <div className="flex items-center justify-between">
      <div><div className="eyebrow">Manage</div><h1 className="font-display text-3xl font-bold text-kGreen">Training Center</h1></div>
      <button onClick={() => setCreating(true)} className="btn-orange"><Plus size={16} /> New course</button>
    </div>

    <div className="mt-7">
      {coursesApi.loading && <LoadingState label="courses" />}
      {!coursesApi.loading && coursesApi.error && <ErrorState message={coursesApi.error} onRetry={coursesApi.reload} />}
      {!coursesApi.loading && !coursesApi.error && coursesApi.items.length === 0 && <EmptyState icon={GraduationCap} title="No courses yet" message="Create your first training course to get started." />}
      {!coursesApi.loading && !coursesApi.error && coursesApi.items.length > 0 && <div className="grid gap-3">
        {coursesApi.items.map(c => <div key={c.id} className="card-k flex items-center justify-between gap-4 p-5">
          <div className="flex items-start gap-3">
            <div className="mt-0.5 grid h-10 w-10 shrink-0 place-items-center rounded-full bg-kTint text-kOrange"><GraduationCap size={18} /></div>
            <div>
              <div className="flex items-center gap-2"><span className="font-semibold text-kInk">{c.title}</span>{c.required && <span className="text-[10px] font-bold uppercase text-red-500">Required</span>}{!c.active && <StatusBadge value="Inactive" />}</div>
              {c.description && <p className="mt-1 text-sm text-kMuted">{c.description}</p>}
              {c.estimated_minutes != null && <p className="mt-1 text-xs text-kMuted">~{c.estimated_minutes} min</p>}
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-3">
            <button onClick={() => setViewingCompletions(c)} className="flex items-center gap-1.5 text-xs font-bold text-kOrange"><Users size={14} /> Progress</button>
            <button onClick={() => toggleActive(c)} className="text-xs font-bold text-kMuted">{c.active ? 'Deactivate' : 'Reactivate'}</button>
          </div>
        </div>)}
      </div>}
    </div>

    {creating && <CourseFormModal onClose={() => setCreating(false)} onSaved={coursesApi.reload} showToast={showToast} />}
    {viewingCompletions && <CompletionsModal course={viewingCompletions} onClose={() => setViewingCompletions(null)} showToast={showToast} />}
  </Shell>
}
