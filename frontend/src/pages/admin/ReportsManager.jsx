import { useState, useEffect, useCallback } from 'react'
import { FileBarChart, Download } from 'lucide-react'
import Shell from '../../components/admin/Shell'
import { LoadingState, ErrorState, errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch, downloadFile } from '../../lib/api'

// One entry per report. `filters` describes the extra (non-date) query
// params this specific report accepts — not every filter makes sense on
// every report, so nothing here is forced onto all of them.
const REPORTS = [
  { key: 'attendance', label: 'Attendance', endpoint: '/api/reports/attendance', dateFilter: true, csv: '/api/reports/attendance/export.csv', filters: [{ name: 'opa_id', label: 'OPA ID' }] },
  { key: 'health', label: 'Health & Wellness', endpoint: '/api/reports/health', dateFilter: true, filters: [{ name: 'opa_id', label: 'OPA ID' }] },
  { key: 'home-visits', label: 'Home Visits', endpoint: '/api/reports/home-visits', dateFilter: true, csv: '/api/reports/home-visits/export.csv', filters: [{ name: 'opa_id', label: 'OPA ID' }, { name: 'volunteer_id', label: 'Volunteer/Staff ID' }] },
  { key: 'volunteers', label: 'Volunteers', endpoint: '/api/reports/volunteers', dateFilter: false, filters: [] },
  { key: 'feeding', label: 'Feeding', endpoint: '/api/reports/feeding', dateFilter: true, filters: [] },
  { key: 'inventory', label: 'Inventory', endpoint: '/api/reports/inventory', dateFilter: true, csv: '/api/reports/inventory/export.csv', filters: [{ name: 'category', label: 'Category' }] },
  { key: 'donations', label: 'Donations', endpoint: '/api/reports/donations', dateFilter: true, filters: [{ name: 'donation_type', label: 'Type (Cash/Food/Equipment)' }] },
  { key: 'activities', label: 'Activities', endpoint: '/api/reports/activities', dateFilter: true, filters: [{ name: 'activity_type', label: 'Activity Type' }, { name: 'status', label: 'Status' }] },
  { key: 'assistance', label: 'Assistance Requests', endpoint: '/api/reports/assistance', dateFilter: true, filters: [{ name: 'request_type', label: 'Request Type' }, { name: 'assigned_to_id', label: 'Assignee ID' }] },
  { key: 'incidents', label: 'Incidents', endpoint: '/api/reports/incidents', dateFilter: true, filters: [{ name: 'incident_type', label: 'Incident Type' }] },
]

function StatCard({ label, value }) { return <div className="card-k p-5"><div className="text-sm text-kMuted">{label}</div><div className="mt-2 font-display text-3xl font-bold text-kGreen">{value}</div></div> }

function CountsTable({ title, counts }) {
  const entries = Object.entries(counts || {})
  if (entries.length === 0) return null
  return <div className="card-k mt-5 overflow-hidden">
    <div className="border-b border-kBorderSoft px-5 py-3 text-sm font-bold text-kGreen">{title}</div>
    <table className="w-full text-left text-sm"><tbody>
      {entries.map(([k, v]) => <tr key={k} className="border-b border-kBorderSoft last:border-0"><td className="px-5 py-3 text-kInk">{k}</td><td className="px-5 py-3 text-right font-semibold text-kMuted">{v}</td></tr>)}
    </tbody></table>
  </div>
}

function ByDateTable({ title, rows, dateKey = 'date', valueKeys }) {
  if (!rows || rows.length === 0) return null
  return <div className="card-k mt-5 overflow-hidden">
    <div className="border-b border-kBorderSoft px-5 py-3 text-sm font-bold text-kGreen">{title}</div>
    <div className="max-h-72 overflow-y-auto"><table className="w-full text-left text-sm"><thead className="sticky top-0 bg-kBorderSoft text-xs uppercase tracking-wider text-kMuted"><tr><th className="px-5 py-3">Date</th>{valueKeys.map(([k, label]) => <th key={k} className="px-5 py-3 text-right">{label}</th>)}</tr></thead><tbody>
      {rows.map((r, i) => <tr key={i} className="border-b border-kBorderSoft last:border-0"><td className="px-5 py-2 text-kInk">{r[dateKey]}</td>{valueKeys.map(([k]) => <td key={k} className="px-5 py-2 text-right text-kMuted">{r[k]}</td>)}</tr>)}
    </tbody></table></div>
  </div>
}

function ReportBody({ reportKey, data }) {
  switch (reportKey) {
    case 'attendance':
      return <>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Registered" value={data.registered_count} />
          <StatCard label="Attendance records" value={data.total_records} />
          <StatCard label="Average daily" value={data.average_daily} />
          <StatCard label="Attendance %" value={`${data.attendance_percentage}%`} />
        </div>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <StatCard label="Highest day" value={data.highest_day} />
          <StatCard label="Lowest day" value={data.lowest_day} />
        </div>
        <ByDateTable title="Attendance by day" rows={data.by_day} valueKeys={[['count', 'Count']]} />
      </>
    case 'health':
      return <>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          <StatCard label="Health checks completed" value={data.health_checks_completed} />
          <StatCard label="Follow-ups required" value={data.follow_ups_required} />
          <StatCard label="Medications started" value={data.medications_started} />
        </div>
        {data.clinic_visits === null && <p className="mt-3 text-xs text-kMuted">Clinic/medical visit tracking is not yet part of the system.</p>}
        <CountsTable title="Wellness trend (recorded wellbeing)" counts={data.wellness_trend} />
        <CountsTable title="Medication administration" counts={data.medication_administration} />
      </>
    case 'home-visits':
      return <>
        <div className="grid gap-4 sm:grid-cols-2">
          <StatCard label="Total visits" value={data.total} />
          <StatCard label="Follow-up required" value={data.follow_up_required} />
        </div>
        <CountsTable title="By status" counts={data.by_status} />
        <CountsTable title="By volunteer/staff" counts={data.by_volunteer} />
      </>
    case 'volunteers':
      return <>
        <div className="grid gap-4 sm:grid-cols-2">
          <StatCard label="Active (verified) volunteers" value={data.active_volunteers} />
        </div>
        <CountsTable title="By status" counts={data.by_status} />
        <div className="card-k mt-5 overflow-hidden">
          <div className="border-b border-kBorderSoft px-5 py-3 text-sm font-bold text-kGreen">Workload</div>
          <div className="overflow-x-auto"><table className="w-full min-w-[600px] text-left text-sm"><thead className="bg-kBorderSoft text-xs uppercase tracking-wider text-kMuted"><tr><th className="px-5 py-3">Volunteer</th><th className="px-5 py-3">Home visits (total/completed)</th><th className="px-5 py-3">Assistance (total/completed)</th><th className="px-5 py-3">Active now</th></tr></thead><tbody>
            {data.workload.map(w => <tr key={w.user_id} className="border-b border-kBorderSoft last:border-0"><td className="px-5 py-3 font-semibold text-kInk">{w.name}</td><td className="px-5 py-3 text-kMuted">{w.home_visits_total} / {w.home_visits_completed}</td><td className="px-5 py-3 text-kMuted">{w.assistance_requests_total} / {w.assistance_requests_completed}</td><td className="px-5 py-3 text-kMuted">{w.active_assignments}</td></tr>)}
            {data.workload.length === 0 && <tr><td colSpan={4} className="px-5 py-6 text-center text-kMuted">No verified volunteers yet.</td></tr>}
          </tbody></table></div>
        </div>
        <p className="mt-3 text-xs text-kMuted">Volunteer hours aren't shown — nothing in the system currently records time-on-task, so we don't fabricate an hours figure from timestamps that don't measure it.</p>
      </>
    case 'feeding':
      return <>
        <div className="grid gap-4 sm:grid-cols-3">
          <StatCard label="Meals planned" value={data.meals_planned} />
          <StatCard label="Meals served" value={data.meals_served} />
          <StatCard label="Attendees with dietary needs" value={data.dietary_flagged_attendees} />
        </div>
        <ByDateTable title="Meals by date" rows={data.meals_by_date} valueKeys={[['attendee_count', 'Attendees']]} />
      </>
    case 'inventory':
      return <>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Items" value={data.items.length} />
          <StatCard label="Low stock" value={data.low_stock_items.length} />
          <StatCard label="Stock in (period)" value={data.stock_in_total} />
          <StatCard label="Stock out (period)" value={data.stock_out_total} />
        </div>
        <p className="mt-3 text-xs text-kMuted">{data.donation_linked_movements} stock-in movement(s) in this period were traced to a logged donation.</p>
        {data.low_stock_items.length > 0 && <div className="card-k mt-5 overflow-hidden">
          <div className="border-b border-kBorderSoft px-5 py-3 text-sm font-bold text-kOrange">Low stock</div>
          <table className="w-full text-left text-sm"><tbody>
            {data.low_stock_items.map(i => <tr key={i.id} className="border-b border-kBorderSoft last:border-0"><td className="px-5 py-2 font-semibold text-kInk">{i.name}</td><td className="px-5 py-2 text-right text-kMuted">{i.current_stock} / {i.minimum_stock} {i.unit}</td></tr>)}
          </tbody></table>
        </div>}
        <ByDateTable title="Movements by date" rows={data.movements_by_date} valueKeys={[['in_total', 'In'], ['out_total', 'Out']]} />
      </>
    case 'donations':
      return <>
        <div className="grid gap-4 sm:grid-cols-2">
          <StatCard label="Total donations" value={data.total_count} />
          <StatCard label="Cash total (KES)" value={Number(data.cash_total).toLocaleString()} />
        </div>
        <CountsTable title="By type" counts={data.by_type} />
        <ByDateTable title="By date" rows={data.by_date} valueKeys={[['count', 'Count']]} />
      </>
    case 'activities':
      return <>
        <div className="grid gap-4 sm:grid-cols-2">
          <StatCard label="Activities conducted" value={data.activities_conducted} />
        </div>
        <CountsTable title="By type" counts={data.by_type} />
        <CountsTable title="Participant status" counts={data.participant_status_breakdown} />
        <ByDateTable title="Activities by date" rows={data.activities_by_date} valueKeys={[['count', 'Count']]} />
      </>
    case 'assistance':
      return <>
        <div className="grid gap-4 sm:grid-cols-2">
          <StatCard label="Total requests" value={data.total} />
          <StatCard label="Completion rate" value={`${data.completion_rate}%`} />
        </div>
        <CountsTable title="By status" counts={data.by_status} />
        <CountsTable title="By type" counts={data.by_type} />
        <CountsTable title="By assignee" counts={data.by_assignee} />
      </>
    case 'incidents':
      return <>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Total incidents" value={data.total} />
          <StatCard label="Open" value={data.open} />
          <StatCard label="Follow-up required" value={data.follow_up_required} />
          <StatCard label="Resolved/Closed" value={data.resolved} />
        </div>
        <CountsTable title="By type" counts={data.by_type} />
        <CountsTable title="By status" counts={data.by_status} />
      </>
    default:
      return null
  }
}

export default function ReportsManager({ showToast }) {
  const [selected, setSelected] = useState(REPORTS[0])
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [extraFilters, setExtraFilters] = useState({})
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const params = new URLSearchParams()
      if (selected.dateFilter && dateFrom) params.set('date_from', dateFrom)
      if (selected.dateFilter && dateTo) params.set('date_to', dateTo)
      selected.filters.forEach(f => { if (extraFilters[f.name]) params.set(f.name, extraFilters[f.name]) })
      const res = await apiFetch(`${selected.endpoint}?${params.toString()}`)
      setData(res.report)
    } catch (err) { setError(errorMessage(err)) }
    finally { setLoading(false) }
  }, [selected, dateFrom, dateTo, extraFilters])

  useEffect(() => { load() }, [load])

  function selectReport(report) {
    setSelected(report)
    setExtraFilters({})
  }

  async function exportCsv() {
    try {
      const params = new URLSearchParams()
      if (selected.dateFilter && dateFrom) params.set('date_from', dateFrom)
      if (selected.dateFilter && dateTo) params.set('date_to', dateTo)
      selected.filters.forEach(f => { if (extraFilters[f.name]) params.set(f.name, extraFilters[f.name]) })
      await downloadFile(`${selected.csv}?${params.toString()}`, `${selected.key}_report.csv`)
    } catch (err) { showToast(errorMessage(err)) }
  }

  return <Shell>
    <div><div className="eyebrow">Management intelligence</div><h1 className="font-display text-3xl font-bold text-kGreen">Reports</h1></div>

    <div className="mt-7 grid gap-6 xl:grid-cols-[220px_1fr]">
      <nav className="card-k grid gap-1 p-3 xl:h-fit">
        {REPORTS.map(r => <button key={r.key} onClick={() => selectReport(r)} className={`flex items-center gap-2 rounded-xl px-3 py-3 text-left text-sm font-semibold ${selected.key === r.key ? 'bg-kTint text-kOrange' : 'text-kInk hover:bg-kCream'}`}><FileBarChart size={16} />{r.label}</button>)}
      </nav>

      <div>
        <div className="card-k flex flex-wrap items-end gap-3 p-5">
          {selected.dateFilter && <>
            <label className="text-sm font-semibold">From<input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} className="input-k mt-2" /></label>
            <label className="text-sm font-semibold">To<input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} className="input-k mt-2" /></label>
          </>}
          {selected.filters.map(f => <label key={f.name} className="text-sm font-semibold">{f.label}<input value={extraFilters[f.name] || ''} onChange={e => setExtraFilters(prev => ({ ...prev, [f.name]: e.target.value }))} className="input-k mt-2" /></label>)}
          {selected.csv && <button onClick={exportCsv} className="btn-orange ml-auto"><Download size={16} /> CSV</button>}
        </div>

        <div className="mt-5">
          {loading ? <LoadingState label="report" /> : error ? <ErrorState message={error} onRetry={load} /> : data && <ReportBody reportKey={selected.key} data={data} />}
        </div>
      </div>
    </div>
  </Shell>
}
