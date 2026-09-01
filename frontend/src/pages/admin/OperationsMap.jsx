import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'
import { MapPin } from 'lucide-react'
import Shell from '../../components/admin/Shell'
import { LoadingState, ErrorState, EmptyState, errorMessage } from '../../components/admin/adminHelpers'
import { apiFetch } from '../../lib/api'

// Vite doesn't resolve Leaflet's default marker PNGs through its normal
// CSS-relative asset lookup — re-point them at the bundled imports once,
// at module scope, before any map instance is created.
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({ iconRetinaUrl: markerIcon2x, iconUrl: markerIcon, shadowUrl: markerShadow })

const NAIROBI_CENTER = [-1.30, 36.78]
const DEFAULT_ZOOM = 13

const LAYER_META = {
  elderly: { label: 'Elderly members', color: '#2f7d5c' },
  home_visits: { label: 'Home visits', color: '#2563eb' },
  assistance: { label: 'Assistance requests', color: '#d97706' },
  incidents: { label: 'Incidents', color: '#dc2626' },
  volunteers: { label: 'Volunteers', color: '#7c3aed' },
}
const ALL_LAYERS = Object.keys(LAYER_META)

function dotIcon(color) {
  return L.divIcon({
    className: '',
    html: `<span style="display:block;width:14px;height:14px;border-radius:9999px;background:${color};border:2px solid #fff;box-shadow:0 0 0 1px rgba(0,0,0,0.25)"></span>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
    popupAnchor: [0, -7],
  })
}

function popupHtml(point) {
  const rows = [
    ['Name', point.name],
    ['Type', point.record_type],
    ['Status', point.status],
  ]
  if (point.assigned_to) rows.push(['Assigned to', point.assigned_to])
  if (point.scheduled_at) rows.push(['Scheduled', new Date(point.scheduled_at).toLocaleString()])
  if (point.severity) rows.push(['Severity', point.severity])
  return `<div style="font-size:13px;line-height:1.5">${rows.map(([k, v]) => `<div><strong>${k}:</strong> ${v}</div>`).join('')}</div>`
}

export default function OperationsMap() {
  const mapContainerRef = useRef(null)
  const mapRef = useRef(null)
  const markersLayerRef = useRef(null)

  const [activeLayers, setActiveLayers] = useState(() => new Set(ALL_LAYERS))
  const [status, setStatus] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  const [points, setPoints] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [reloadKey, setReloadKey] = useState(0)

  // Init the map once.
  useEffect(() => {
    if (mapRef.current) return
    const map = L.map(mapContainerRef.current).setView(NAIROBI_CENTER, DEFAULT_ZOOM)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map)
    markersLayerRef.current = L.layerGroup().addTo(map)
    mapRef.current = map
    return () => { map.remove(); mapRef.current = null }
  }, [])

  // Fetch points whenever filters change.
  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError('')
      try {
        const params = new URLSearchParams()
        if (activeLayers.size > 0 && activeLayers.size < ALL_LAYERS.length) {
          params.set('layers', Array.from(activeLayers).join(','))
        } else if (activeLayers.size === 0) {
          params.set('layers', '')
        }
        if (status) params.set('status', status)
        if (dateFrom) params.set('date_from', dateFrom)
        if (dateTo) params.set('date_to', dateTo)
        const data = await apiFetch(`/api/operations/map?${params.toString()}`)
        if (!cancelled) setPoints(activeLayers.size === 0 ? [] : data.points)
      } catch (err) {
        if (!cancelled) setError(errorMessage(err))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [activeLayers, status, dateFrom, dateTo, reloadKey])

  // Render markers whenever points change.
  useEffect(() => {
    const layerGroup = markersLayerRef.current
    if (!layerGroup) return
    layerGroup.clearLayers()
    points.forEach(point => {
      if (point.latitude == null || point.longitude == null) return
      const color = LAYER_META[point.layer]?.color || '#64748b'
      L.marker([point.latitude, point.longitude], { icon: dotIcon(color) })
        .bindPopup(popupHtml(point))
        .addTo(layerGroup)
    })
  }, [points])

  function toggleLayer(layer) {
    setActiveLayers(prev => {
      const next = new Set(prev)
      if (next.has(layer)) next.delete(layer)
      else next.add(layer)
      return next
    })
  }

  const isEmpty = !loading && !error && points.length === 0

  return <Shell>
    <div><div className="eyebrow">Operations</div><h1 className="font-display text-3xl font-bold text-kGreen">Operations Map</h1></div>
    <p className="mt-2 max-w-2xl text-sm text-kMuted">A geocoded view of elderly members, home visits, assistance requests, incidents, and volunteers — approximate locations only, no exact addresses or health details.</p>

    <div className="mt-6 flex flex-wrap items-end gap-4">
      <div className="flex flex-wrap gap-3">
        {ALL_LAYERS.map(layer => <label key={layer} className="flex items-center gap-2 rounded-xl border border-kBorderSoft px-3 py-2 text-sm font-semibold">
          <input type="checkbox" checked={activeLayers.has(layer)} onChange={() => toggleLayer(layer)} className="h-4 w-4" />
          <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: LAYER_META[layer].color }} />
          {LAYER_META[layer].label}
        </label>)}
      </div>
      <label className="text-xs font-semibold text-kMuted">Status<input value={status} onChange={e => setStatus(e.target.value)} placeholder="e.g. Active, Pending" className="input-k mt-1 w-40" /></label>
      <label className="text-xs font-semibold text-kMuted">From<input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} className="input-k mt-1" /></label>
      <label className="text-xs font-semibold text-kMuted">To<input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} className="input-k mt-1" /></label>
    </div>

    <div className="mt-4 flex flex-wrap items-center gap-4 text-xs text-kMuted">
      <span className="font-bold uppercase tracking-wide">Legend</span>
      {ALL_LAYERS.map(layer => <span key={layer} className="flex items-center gap-1.5"><span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: LAYER_META[layer].color }} /> {LAYER_META[layer].label}</span>)}
    </div>

    {loading && <LoadingState label="map data" rows={3} />}
    {!loading && error && <ErrorState message={error} onRetry={() => setReloadKey(k => k + 1)} />}

    <div className={`mt-4 overflow-hidden rounded-2xl border border-kBorderSoft ${loading || error ? 'hidden' : ''}`}>
      <div ref={mapContainerRef} style={{ height: '65vh', width: '100%' }} />
    </div>

    {isEmpty && <EmptyState icon={MapPin} title="No geocoded records to show yet" message="Nothing matches the current layer/status/date filters." />}
  </Shell>
}
