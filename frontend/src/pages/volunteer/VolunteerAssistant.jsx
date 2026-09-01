import { useState } from 'react'
import { Sparkles, Send } from 'lucide-react'
import VolunteerShell from '../../components/volunteer/VolunteerShell'
import { LoadingState, ErrorState, errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch } from '../../lib/api'

const SUGGESTED_PROMPTS = [
  "What's my schedule today?",
  'How many hours have I served?',
  'What training do I still need?',
  'Do I have unread messages?',
]

function fmtKey(k) { return k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) }
function fmtCell(v) { return v === null || v === undefined || v === '' ? '—' : String(v) }

function ResultsTable({ rows }) {
  if (!rows || rows.length === 0) return <p className="mt-2 text-sm text-kMuted">No matching records.</p>
  const columns = Object.keys(rows[0])
  return <div className="mt-2 overflow-x-auto rounded-xl border border-kBorderSoft">
    <table className="w-full min-w-[400px] text-left text-sm">
      <thead className="bg-kCream text-xs uppercase tracking-wide text-kMuted"><tr>{columns.map(c => <th key={c} className="px-3 py-2">{fmtKey(c)}</th>)}</tr></thead>
      <tbody>{rows.map((row, i) => <tr key={i} className="border-t border-kBorderSoft">{columns.map(c => <td key={c} className="px-3 py-2 text-kInk">{fmtCell(row[c])}</td>)}</tr>)}</tbody>
    </table>
  </div>
}

function PromptChips({ prompts, onPick }) {
  return <div className="flex flex-wrap gap-2">
    {prompts.map(p => <button key={p} onClick={() => onPick(p)} className="rounded-full border border-kBorderSoft px-3 py-1.5 text-xs font-semibold text-kInk hover:border-kOrange hover:text-kOrange">{p}</button>)}
  </div>
}

export default function VolunteerAssistant() {
  const [question, setQuestion] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [asked, setAsked] = useState(false)

  async function ask(q) {
    const trimmed = (q ?? question).trim()
    if (!trimmed) return
    setQuestion(trimmed)
    setLoading(true)
    setError('')
    setAsked(true)
    try { setResult(await apiFetch('/api/ai/volunteer/query', { method: 'POST', body: { question: trimmed } })) }
    catch (err) { setError(errorMessage(err)); setResult(null) }
    finally { setLoading(false) }
  }

  function submit(e) { e.preventDefault(); ask() }

  return <VolunteerShell>
    <div><div className="eyebrow">Smart Features</div><h1 className="flex items-center gap-2 font-display text-3xl font-bold text-kGreen"><Sparkles className="text-kOrange" /> Ask KDCCE</h1></div>
    <p className="mt-2 max-w-xl text-sm text-kMuted">Ask about your schedule, hours, training, or messages.</p>

    <form onSubmit={submit} className="mt-6 flex gap-2">
      <input value={question} onChange={e => setQuestion(e.target.value)} placeholder="Ask about your schedule, hours, training..." className="input-k flex-1" />
      <button disabled={loading} className="btn-orange shrink-0 disabled:opacity-60"><Send size={16} /> {loading ? 'Asking…' : 'Ask'}</button>
    </form>

    <div className="mt-3"><PromptChips prompts={SUGGESTED_PROMPTS} onPick={ask} /></div>

    <div className="mt-6">
      {loading && <LoadingState label="response" />}
      {!loading && error && <ErrorState message={error} onRetry={() => ask(question)} />}
      {!loading && !error && result && result.supported && <div className="card-k p-6">
        <p className="font-display text-lg font-bold text-kInk">{result.ai_explanation}</p>
        <ResultsTable rows={Array.isArray(result.results) ? result.results : []} />
      </div>}
      {!loading && !error && result && !result.supported && <div className="card-k p-6">
        <p className="text-sm font-semibold text-kInk">{result.message}</p>
        <div className="mt-3"><PromptChips prompts={result.examples} onPick={ask} /></div>
      </div>}
      {!loading && !error && !asked && <div className="card-k p-10 text-center">
        <div className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-kTint text-kOrange"><Sparkles size={22} /></div>
        <p className="mt-4 text-sm font-bold text-kInk">Ask anything about your own work</p>
        <p className="mt-1 text-sm text-kMuted">Try one of the suggested questions above, or type your own.</p>
      </div>}
    </div>
  </VolunteerShell>
}
