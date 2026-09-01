const STYLES = {
  // Priority
  Critical: 'bg-red-500/15 text-red-500',
  High: 'bg-orange-500/15 text-orange-500',
  Urgent: 'bg-red-500/15 text-red-500',
  Medium: 'bg-amber-500/15 text-amber-600 dark:text-amber-400',
  Low: 'bg-slate-500/15 text-slate-500',
  // Status
  Open: 'bg-red-500/15 text-red-500',
  New: 'bg-blue-500/15 text-blue-500',
  Pending: 'bg-amber-500/15 text-amber-600 dark:text-amber-400',
  Requested: 'bg-amber-500/15 text-amber-600 dark:text-amber-400',
  Matching: 'bg-amber-500/15 text-amber-600 dark:text-amber-400',
  Assigned: 'bg-purple-500/15 text-purple-500',
  Accepted: 'bg-purple-500/15 text-purple-500',
  Scheduled: 'bg-purple-500/15 text-purple-500',
  Started: 'bg-blue-500/15 text-blue-500',
  'In Progress': 'bg-blue-500/15 text-blue-500',
  'Under Review': 'bg-blue-500/15 text-blue-500',
  Completed: 'bg-emerald-500/15 text-emerald-500',
  Resolved: 'bg-emerald-500/15 text-emerald-500',
  Verified: 'bg-emerald-500/15 text-emerald-500',
  Cancelled: 'bg-slate-500/15 text-slate-500',
  Closed: 'bg-slate-500/15 text-slate-500',
  Rejected: 'bg-red-500/15 text-red-500',
  Published: 'bg-emerald-500/15 text-emerald-500',
  Draft: 'bg-slate-500/15 text-slate-500',
  // Elderly member record status
  Active: 'bg-emerald-500/15 text-emerald-500',
  Inactive: 'bg-slate-500/15 text-slate-500',
  Deceased: 'bg-slate-500/15 text-slate-500',
  Transferred: 'bg-amber-500/15 text-amber-600 dark:text-amber-400',
  // Activity participant status
  Registered: 'bg-slate-500/15 text-slate-500',
  Attended: 'bg-emerald-500/15 text-emerald-500',
  'No-show': 'bg-red-500/15 text-red-500',
  // Donation payment status
  Paid: 'bg-emerald-500/15 text-emerald-500',
  Received: 'bg-emerald-500/15 text-emerald-500',
  // Announcement priority/status
  Normal: 'bg-slate-500/15 text-slate-500',
  Important: 'bg-amber-500/15 text-amber-600 dark:text-amber-400',
  Expired: 'bg-slate-500/15 text-slate-500',
}

export default function StatusBadge({ value, className = '' }) {
  if (!value) return null
  const style = STYLES[value] || 'bg-slate-500/15 text-slate-500'
  return <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-bold ${style} ${className}`}>{value}</span>
}
