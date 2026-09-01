import { useState, useEffect, useCallback } from 'react'
import { CheckCircle2, Clock, ExternalLink, GraduationCap, PlayCircle } from 'lucide-react'
import VolunteerShell from '../../components/volunteer/VolunteerShell'
import StatusBadge from '../../components/admin/StatusBadge'
import { LoadingState, ErrorState, errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch } from '../../lib/api'

function CourseCard({ course, onAdvance, busy }) {
  const status = course.progress.status
  return <div className="card-k p-5">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="font-display text-base font-bold text-kInk">{course.title}</h3>
          {course.required && <span className="rounded-full bg-red-500/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-red-500">Required</span>}
        </div>
        {course.description && <p className="mt-1 text-sm text-kMuted">{course.description}</p>}
        <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-kMuted">
          {course.category && <span>{course.category}</span>}
          {course.estimated_minutes && <span className="flex items-center gap-1"><Clock size={12} /> {course.estimated_minutes} min</span>}
          {course.resource_url && <a href={course.resource_url} target="_blank" rel="noreferrer" className="flex items-center gap-1 font-semibold text-kOrange"><ExternalLink size={12} /> Open resource</a>}
        </div>
      </div>
      <StatusBadge value={status} />
    </div>
    <div className="mt-4 flex gap-3">
      {status === 'Not Started' && <button disabled={busy} onClick={() => onAdvance(course.id, 'In Progress')} className="btn-orange disabled:opacity-60"><PlayCircle size={15} /> Start</button>}
      {status === 'In Progress' && <button disabled={busy} onClick={() => onAdvance(course.id, 'Completed')} className="btn-orange disabled:opacity-60"><CheckCircle2 size={15} /> Mark complete</button>}
      {status === 'Completed' && <span className="flex items-center gap-1.5 text-sm font-semibold text-emerald-500"><CheckCircle2 size={15} /> Completed {course.progress.completed_at ? new Date(course.progress.completed_at).toLocaleDateString([], { dateStyle: 'medium' }) : ''}</span>}
    </div>
  </div>
}

export default function TrainingCenter({ showToast }) {
  const [courses, setCourses] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busyId, setBusyId] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try { setCourses((await apiFetch('/api/training/me/progress')).courses) }
    catch (err) { setError(errorMessage(err)) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  async function advance(courseId, status) {
    setBusyId(courseId)
    try {
      await apiFetch(`/api/training/me/progress/${courseId}`, { method: 'PATCH', body: { status } })
      showToast(status === 'Completed' ? 'Course completed — nice work!' : 'Course started')
      load()
    } catch (err) { showToast(errorMessage(err)) }
    finally { setBusyId(null) }
  }

  const required = courses.filter(c => c.required)
  const optional = courses.filter(c => !c.required)
  const completedCount = courses.filter(c => c.progress.status === 'Completed').length

  return <VolunteerShell>
    <div><div className="eyebrow">Grow with us</div><h1 className="font-display text-3xl font-bold text-kGreen">Training Center</h1></div>

    {loading ? <LoadingState label="training" /> : error ? <ErrorState message={error} onRetry={load} /> : <>
      <div className="mt-7 card-k flex items-center gap-4 p-6">
        <div className="grid h-12 w-12 shrink-0 place-items-center rounded-xl bg-kTint text-kOrange"><GraduationCap size={22} /></div>
        <div><div className="font-display text-xl font-bold text-kInk">{completedCount} of {courses.length} completed</div><div className="text-sm text-kMuted">Keep going — every course you finish counts toward your training achievements.</div></div>
      </div>

      {required.length > 0 && <>
        <h2 className="mt-7 text-xs font-bold uppercase tracking-wide text-kMuted">Required</h2>
        <div className="mt-3 grid gap-3">{required.map(c => <CourseCard key={c.id} course={c} onAdvance={advance} busy={busyId === c.id} />)}</div>
      </>}

      {optional.length > 0 && <>
        <h2 className="mt-7 text-xs font-bold uppercase tracking-wide text-kMuted">Optional</h2>
        <div className="mt-3 grid gap-3">{optional.map(c => <CourseCard key={c.id} course={c} onAdvance={advance} busy={busyId === c.id} />)}</div>
      </>}

      {courses.length === 0 && <div className="card-k mt-7 p-10 text-center text-sm text-kMuted">No training courses are available yet.</div>}
    </>}
  </VolunteerShell>
}
