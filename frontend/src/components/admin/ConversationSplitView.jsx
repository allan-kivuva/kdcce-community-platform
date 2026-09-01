import { ArrowLeft, Search } from 'lucide-react'
import { LoadingState, ErrorState } from './adminHelpers'

/** The shared "modern inbox" shell — a left conversation list (search,
 * unread dot, last-message preview, timestamp) and a right thread pane —
 * used identically by the admin Messages page and the volunteer Messages
 * page. Each caller assembles its own `items` (direct conversations,
 * assignment threads, whatever mix makes sense for that role) and
 * supplies the thread content as `children`; this component only owns
 * the responsive list/detail layout and the "which one is selected"
 * plumbing, not any messaging-specific fetch/send logic.
 *
 * Mobile: the list is the default view; selecting an item swaps to a
 * dedicated thread view with a back button, never both panes at once —
 * `md:` breakpoints bring back the side-by-side split-pane layout. */
export default function ConversationSplitView({
  items, selectedKey, onSelect, loading, error, onRetry, search, headerActions, emptyMessage, children,
}) {
  const hasSelection = selectedKey != null

  // The full-pane loading/error state only ever replaces the *list* —
  // never the open thread. A background refresh (e.g. the reload a sent
  // reply or a mark-as-read triggers) must not blank an already-open
  // conversation; if it did, the thread pane's own children would
  // unmount and remount on every refresh, re-firing its own mount
  // effects (mark-read → reload → unmount → remount → mark-read → ...)
  // in a loop. So: show the takeover skeleton/error only before there's
  // ever been a selection to preserve.
  if (loading && !hasSelection) return <LoadingState label="conversations" />
  if (error && !hasSelection) return <ErrorState message={error} onRetry={onRetry} />

  return <div className="card-k mt-7 grid overflow-hidden md:grid-cols-[320px_1fr]" style={{ minHeight: '32rem' }}>
    <div className={`flex flex-col border-kBorderSoft md:border-r ${hasSelection ? 'hidden md:flex' : 'flex'}`}>
      <div className="border-b border-kBorderSoft p-3">
        <div className="flex items-center justify-between gap-2">
          <div className="relative flex-1"><Search className="absolute left-2.5 top-2.5 text-kMuted" size={15} /><input value={search.value} onChange={e => search.onChange(e.target.value)} className="input-k py-2 pl-8 text-sm" placeholder="Search..." /></div>
          {headerActions}
        </div>
      </div>
      <div className="flex-1 overflow-y-auto">
        {error && <p className="p-4 text-center text-sm text-kOrange">{error}</p>}
        {!error && items.length === 0 && <p className="p-6 text-center text-sm text-kMuted">{loading ? 'Loading…' : (emptyMessage || 'Nothing here yet.')}</p>}
        {items.map(it => <button key={it.key} onClick={() => onSelect(it.key)} className={`flex w-full items-start gap-3 border-b border-kBorderSoft p-3 text-left transition hover:bg-kTint ${selectedKey === it.key ? 'bg-kTint' : ''}`}>
          <div className="relative shrink-0">
            <div className="grid h-10 w-10 place-items-center rounded-full bg-kOrange/15 text-kOrange">{it.icon}</div>
            {it.unread && <span className="absolute -right-0.5 -top-0.5 h-3 w-3 rounded-full border-2 border-kSurface bg-kOrange" />}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between gap-2">
              <span className={`truncate text-sm ${it.unread ? 'font-bold text-kInk' : 'font-semibold text-kInk'}`}>{it.title}</span>
              <span className="shrink-0 text-[10px] text-kMuted">{it.timestamp}</span>
            </div>
            <div className="mt-0.5 flex items-center justify-between gap-2">
              <span className="truncate text-xs text-kMuted">{it.subtitle}</span>
              {it.badge != null && it.badge > 0 && <span className="shrink-0 rounded-full bg-kOrange px-1.5 text-[10px] font-bold text-white">{it.badge}</span>}
            </div>
            {it.preview && <p className="mt-1 truncate text-xs text-kMuted">{it.preview}</p>}
          </div>
        </button>)}
      </div>
    </div>

    <div className={`flex-col ${hasSelection ? 'flex' : 'hidden md:flex'}`}>
      {hasSelection ? <>
        <button onClick={() => onSelect(null)} className="flex items-center gap-2 border-b border-kBorderSoft p-3 text-sm font-semibold text-kOrange md:hidden"><ArrowLeft size={15} /> Back to conversations</button>
        {children}
      </> : <div className="grid flex-1 place-items-center p-10 text-center text-sm text-kMuted">Select a conversation to view it here.</div>}
    </div>
  </div>
}
