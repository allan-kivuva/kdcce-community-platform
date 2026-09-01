import { useState } from 'react'
import { AlertTriangle, CheckCircle2, Upload } from 'lucide-react'
import Shell from '../../components/admin/Shell'
import { errorMessage } from '../../components/admin/adminHelpers'
import { uploadForm } from '../../lib/api'

const ENTITIES = [
  { value: 'elderly_members', label: 'Elderly members', columns: 'full_name, date_of_birth, gender, location, opa_id, emergency_contact_name, emergency_contact_phone, emergency_contact_relationship, vulnerability_notes, health_notes, allergies, dietary_requirements, status (required: full_name, gender)' },
  { value: 'inventory_items', label: 'Inventory items', columns: 'name, category, unit, minimum_stock, notes (required: name, unit)' },
  { value: 'programs', label: 'Programs', columns: 'name, slug, description, category, status, start_date, end_date, coordinator_id, location, target_population, goals, image_url (required: name)' },
]

function SummaryLine({ preview }) {
  return <p className="text-sm font-semibold text-kInk">
    {preview.valid_count} of {preview.total} row(s) are valid, {preview.error_count} have errors, {preview.duplicate_count} {preview.duplicate_count === 1 ? 'is' : 'are'} duplicate.
  </p>
}

function PreviewTable({ rows }) {
  return <div className="mt-4 overflow-x-auto rounded-2xl border border-kBorderSoft">
    <table className="w-full text-left text-sm" style={{ minWidth: 700 }}>
      <thead className="bg-kBorderSoft text-xs uppercase tracking-wider text-kMuted">
        <tr><th className="px-4 py-3">Row</th><th className="px-4 py-3">Data</th><th className="px-4 py-3">Flags</th></tr>
      </thead>
      <tbody>
        {rows.map(row => <tr key={row.row_number} className="border-b border-kBorderSoft last:border-0 align-top">
          <td className="px-4 py-3 font-semibold text-kInk">{row.row_number}</td>
          <td className="px-4 py-3 text-xs text-kMuted">
            {Object.entries(row.data).map(([k, v]) => <div key={k}><span className="font-semibold text-kInk">{k}:</span> {v}</div>)}
            {Object.keys(row.data).length === 0 && <span>(empty row)</span>}
          </td>
          <td className="px-4 py-3">
            {row.is_duplicate && <span className="mr-1 inline-block rounded-full bg-amber-500/15 px-2.5 py-1 text-xs font-bold text-amber-600">Duplicate</span>}
            {Object.keys(row.errors).length > 0 && <div className="mt-1 grid gap-0.5">
              {Object.entries(row.errors).map(([field, msgs]) => <span key={field} className="inline-block w-fit rounded-full bg-red-500/15 px-2.5 py-1 text-xs font-bold text-red-500">{field}: {(Array.isArray(msgs) ? msgs : [msgs]).join(', ')}</span>)}
            </div>}
            {!row.is_duplicate && Object.keys(row.errors).length === 0 && <span className="text-xs font-bold text-emerald-500">Valid</span>}
          </td>
        </tr>)}
      </tbody>
    </table>
  </div>
}

export default function ImportsManager() {
  const [step, setStep] = useState('upload') // upload | preview | results
  const [entity, setEntity] = useState('elderly_members')
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  function reset() {
    setStep('upload')
    setFile(null)
    setPreview(null)
    setResult(null)
    setError('')
  }

  async function runPreview(e) {
    e.preventDefault()
    if (!file) return
    setBusy(true)
    setError('')
    try {
      const formData = new FormData()
      formData.append('file', file)
      const data = await uploadForm(`/api/imports/${entity}/preview`, formData)
      setPreview(data)
      setStep('preview')
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  async function runCommit() {
    if (!file) return
    setBusy(true)
    setError('')
    try {
      const formData = new FormData()
      formData.append('file', file)
      const data = await uploadForm(`/api/imports/${entity}/commit`, formData)
      setResult(data)
      setStep('results')
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const selectedEntity = ENTITIES.find(en => en.value === entity)

  return <Shell>
    <div><div className="eyebrow">Data</div><h1 className="font-display text-3xl font-bold text-kGreen">Imports</h1></div>
    <p className="mt-2 max-w-2xl text-sm text-kMuted">Bulk-import elderly members, inventory items, or programs from a CSV file — nothing is written to the database until you confirm the preview.</p>

    {error && <div className="mt-4 flex items-center gap-2 rounded-xl bg-red-500/10 px-4 py-3 text-sm font-semibold text-red-500"><AlertTriangle size={16} /> {error}</div>}

    {step === 'upload' && <div className="card-k mt-6 p-6">
      <form onSubmit={runPreview} className="grid gap-4 max-w-md">
        <label className="text-sm font-semibold">What are you importing?
          <select value={entity} onChange={e => setEntity(e.target.value)} className="input-k mt-2">
            {ENTITIES.map(en => <option key={en.value} value={en.value}>{en.label}</option>)}
          </select>
        </label>
        <p className="text-xs text-kMuted">Expected columns: {selectedEntity.columns}</p>
        <label className="text-sm font-semibold">CSV file
          <input type="file" accept=".csv" onChange={e => setFile(e.target.files?.[0] || null)} className="input-k mt-2" required />
        </label>
        <button disabled={!file || busy} className="btn-orange w-fit disabled:opacity-60">{busy ? 'Uploading…' : 'Preview'}</button>
      </form>
    </div>}

    {step === 'preview' && preview && <div className="mt-6">
      <div className="card-k p-6">
        <SummaryLine preview={preview} />
        <PreviewTable rows={preview.rows} />
        <div className="mt-5 flex items-center gap-3">
          <button disabled={preview.valid_count === 0 || busy} onClick={runCommit} className="btn-orange disabled:opacity-60">{busy ? 'Importing…' : 'Confirm import'}</button>
          <button onClick={reset} className="text-sm font-semibold text-kMuted">Start over</button>
        </div>
      </div>
    </div>}

    {step === 'results' && result && <div className="mt-6 card-k p-6">
      <div className="flex items-center gap-2 text-emerald-500"><CheckCircle2 size={20} /><span className="font-display text-lg font-bold">{result.created_count} of {result.total} row(s) imported</span></div>
      {result.skipped.length > 0 && <div className="mt-4">
        <div className="text-xs font-bold uppercase tracking-wide text-kMuted">Skipped rows</div>
        <div className="mt-2 grid gap-2">
          {result.skipped.map(s => <div key={s.row_number} className="rounded-xl bg-kCream px-4 py-3 text-sm">
            <span className="font-semibold text-kInk">Row {s.row_number}</span> — {s.reason === 'duplicate' ? 'duplicate record' : 'validation error'}
            {s.errors && <div className="mt-1 grid gap-0.5 text-xs text-red-500">{Object.entries(s.errors).map(([field, msgs]) => <span key={field}>{field}: {(Array.isArray(msgs) ? msgs : [msgs]).join(', ')}</span>)}</div>}
          </div>)}
        </div>
      </div>}
      <button onClick={reset} className="btn-orange mt-5"><Upload size={16} /> Start another import</button>
    </div>}
  </Shell>
}
