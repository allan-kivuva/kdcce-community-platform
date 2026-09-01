import { useState, useEffect, useCallback } from 'react'
import { Sparkles, Send, Bot, AlertTriangle } from 'lucide-react'
import Shell from '../../components/admin/Shell'
import { LoadingState, ErrorState, errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch } from '../../lib/api'

const SUGGESTED_PROMPTS = [
  'How many visits are scheduled today?',
  'Show unassigned assistance requests.',
  'Which volunteers are available Saturday?',
  'Which elderly members have not received a home visit in 30 days?',
  'Show unresolved high-priority concerns.',
  'Which programs had the highest attendance this month?',
  'How much has the Feeding Program spent this month?',
  'Show campaigns below 50% of their goal.',
  'Which volunteers have the highest service hours this quarter?',
  "Summarize today's operational risks.",
]

const RISK_SECTIONS = [
  ['high_priority_concerns', 'High-priority concerns'],
  ['unassigned_requests', 'Unassigned requests'],
  ['low_stock_items', 'Low stock items'],
  ['members_without_recent_visits', 'Members without recent visits'],
]

function fmtKey(k) { return k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) }
function fmtCell(v) { return v === null || v === undefined || v === '' ? '—' : String(v) }

function ResultsTable({ rows }) {
  if (!rows || rows.length === 0) return <p className="mt-2 text-sm text-kMuted">No matching records.</p>
  const columns = Object.keys(rows[0])
  return <div className="mt-2 overflow-x-auto rounded-xl border border-kBorderSoft">
    <table className="w-full min-w-[480px] text-left text-sm">
      <thead className="bg-kCream text-xs uppercase tracking-wide text-kMuted"><tr>{columns.map(c => <th key={c} className="px-3 py-2">{fmtKey(c)}</th>)}</tr></thead>
      <tbody>{rows.map((row, i) => <tr key={i} className="border-t border-kBorderSoft">{columns.map(c => <td key={c} className="px-3 py-2 text-kInk">{fmtCell(row[c])}</td>)}</tr>)}</tbody>
    </table>
  </div>
}

function ResultsBlock({ intent, results }) {
  if (intent === 'OPERATIONAL_RISK_SUMMARY' && results && !Array.isArray(results)) {
    return <div className="mt-4 grid gap-4">
      {RISK_SECTIONS.map(([key, label]) => <div key={key}>
        <div className="text-xs font-bold uppercase tracking-wide text-kMuted">{label} ({(results[key] || []).length})</div>
        <ResultsTable rows={results[key] || []} />
      </div>)}
    </div>
  }
  return <ResultsTable rows={Array.isArray(results) ? results : []} />
}

function AiStatusBadge({ enabled }) {
  return <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-bold ${enabled ? 'bg-emerald-500/15 text-emerald-500' : 'bg-slate-500/15 text-slate-500'}`}>
    <Bot size={13} /> AI: {enabled ? 'On' : 'Off'}
  </span>
}

function PromptChips({ prompts, onPick }) {
  return <div className="flex flex-wrap gap-2">
    {prompts.map(p => <button key={p} onClick={() => onPick(p)} className="rounded-full border border-kBorderSoft px-3 py-1.5 text-xs font-semibold text-kInk hover:border-kOrange hover:text-kOrange">{p}</button>)}
  </div>
}

function BriefingSection() {
  const [briefing, setBriefing] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showText, setShowText] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try { setBriefing(await apiFetch('/api/ai/admin/briefing')) }
    catch (err) { setError(errorMessage(err)) }
    finally { setLoading(false) }
  }, [])
  useEffect(() => { load() }, [load])

  if (loading) return <div className="mt-6"><LoadingState label="daily briefing" /></div>
  if (error) return <div className="mt-6"><ErrorState message={error} onRetry={load} /></div>

  const f = briefing.facts
  const n = f.needs_attention
  const attentionItems = [
    ...n.members_without_recent_visits.map(m => `${m.member_name} has had no visit in over 30 days`),
    ...n.stale_concerns.map(c => `Concern #${c.id} has been open ${c.days_open} day(s)`),
    ...n.low_stock_items.map(i => `${i.name} stock is below threshold (${i.current_stock} ${i.unit})`),
    ...n.understaffed_programs.map(p => `${p.title} still needs ${p.spots_short} volunteer(s)`),
  ]

  return <div className="card-k mt-6 p-6">
    <div className="flex items-center justify-between">
      <h2 className="font-display text-lg font-bold text-kGreen">Daily briefing</h2>
      <button onClick={() => setShowText(s => !s)} className="text-xs font-bold text-kOrange">{showText ? 'Hide narrative' : 'View as text'}</button>
    </div>

    <div className="mt-4 grid gap-4 sm:grid-cols-3">
      <div className="rounded-xl bg-kTint p-4 text-center"><div className="font-display text-2xl font-bold text-kOrange">{f.today.visits_scheduled}</div><div className="text-xs text-kMuted">Visits scheduled</div></div>
      <div className="rounded-xl bg-kTint p-4 text-center"><div className="font-display text-2xl font-bold text-kInk">{f.today.unassigned_requests}</div><div className="text-xs text-kMuted">Unassigned requests</div></div>
      <div className={`rounded-xl p-4 text-center ${f.today.high_priority_concerns_open > 0 ? 'bg-red-500/10' : 'bg-kTint'}`}><div className={`font-display text-2xl font-bold ${f.today.high_priority_concerns_open > 0 ? 'text-red-500' : 'text-kInk'}`}>{f.today.high_priority_concerns_open}</div><div className="text-xs text-kMuted">High-priority concerns</div></div>
    </div>

    <div className="mt-5 grid gap-5 sm:grid-cols-2">
      <div>
        <h3 className="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-kMuted"><AlertTriangle size={13} /> Needs attention</h3>
        {attentionItems.length === 0 ? <p className="mt-2 text-sm text-kMuted">Nothing notable right now.</p> : <ul className="mt-2 grid gap-1.5 text-sm text-kInk">{attentionItems.map((t, i) => <li key={i}>{t}</li>)}</ul>}
      </div>
      <div>
        <h3 className="text-xs font-bold uppercase tracking-wide text-kMuted">Recent activity</h3>
        <ul className="mt-2 grid gap-1.5 text-sm text-kInk">
          <li>{f.recent_activity.visits_completed_yesterday} visit(s) completed yesterday</li>
          <li>{f.recent_activity.achievements_awarded_yesterday} achievement(s) awarded yesterday</li>
        </ul>
      </div>
    </div>

    {showText && <pre className="mt-5 whitespace-pre-wrap rounded-xl bg-kCream p-4 font-sans text-sm text-kInk">{briefing.briefing_text}</pre>}
  </div>
}

export default function AIAssistant() {
  const [status, setStatus] = useState(null)
  const [question, setQuestion] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [asked, setAsked] = useState(false)

  useEffect(() => { apiFetch('/api/ai/admin/status').then(setStatus).catch(() => {}) }, [])

  async function ask(q) {
    const trimmed = (q ?? question).trim()
    if (!trimmed) return
    setQuestion(trimmed)
    setLoading(true)
    setError('')
    setAsked(true)
    try { setResult(await apiFetch('/api/ai/admin/query', { method: 'POST', body: { question: trimmed } })) }
    catch (err) { setError(errorMessage(err)); setResult(null) }
    finally { setLoading(false) }
  }

  function submit(e) { e.preventDefault(); ask() }

  return <Shell>
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div><div className="eyebrow">Smart Features</div><h1 className="flex items-center gap-2 font-display text-3xl font-bold text-kGreen"><Sparkles className="text-kOrange" /> AI Assistant</h1></div>
      {status && <AiStatusBadge enabled={status.ai_enabled} />}
    </div>
    <p className="mt-2 max-w-2xl text-sm text-kMuted">Ask a question about visits, volunteers, requests, programs, or finances. Answers are always grounded in real records — AI narration, when available, only rephrases what's already true.</p>

    <form onSubmit={submit} className="mt-6 flex gap-2">
      <input value={question} onChange={e => setQuestion(e.target.value)} placeholder="Ask about visits, volunteers, programs..." className="input-k flex-1" />
      <button disabled={loading} className="btn-orange shrink-0 disabled:opacity-60"><Send size={16} /> {loading ? 'Asking…' : 'Ask'}</button>
    </form>

    <div className="mt-3"><PromptChips prompts={SUGGESTED_PROMPTS} onPick={ask} /></div>

    <div className="mt-6">
      {loading && <LoadingState label="response" />}
      {!loading && error && <ErrorState message={error} onRetry={() => ask(question)} />}
      {!loading && !error && result && result.supported && <div className="card-k p-6">
        <p className="font-display text-lg font-bold text-kInk">{result.ai_explanation}</p>
        <ResultsBlock intent={result.intent} results={result.results} />
      </div>}
      {!loading && !error && result && !result.supported && <div className="card-k p-6">
        <p className="text-sm font-semibold text-kInk">{result.message}</p>
        <div className="mt-3"><PromptChips prompts={result.examples} onPick={ask} /></div>
      </div>}
      {!loading && !error && !asked && <div className="card-k p-10 text-center">
        <div className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-kTint text-kOrange"><Sparkles size={22} /></div>
        <p className="mt-4 text-sm font-bold text-kInk">Ask anything about today's operations</p>
        <p className="mt-1 text-sm text-kMuted">Try one of the suggested questions above, or type your own.</p>
      </div>}
    </div>

    <BriefingSection />
  </Shell>
}
