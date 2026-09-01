// Tiny inline trend line for a StatCard — takes a plain array of numbers
// (already-aggregated counts, e.g. one per day) and draws it full-width.
// No charting library: this is one polyline, not worth a dependency.
export default function MiniSparkline({ data, color = '#3b82f6', height = 36 }) {
  if (!data || data.length < 2) return null
  const max = Math.max(...data, 1)
  const min = Math.min(...data, 0)
  const range = max - min || 1
  const width = 100
  const step = width / (data.length - 1)
  const points = data.map((v, i) => `${i * step},${height - ((v - min) / range) * (height - 4) - 2}`).join(' ')
  const areaPoints = `0,${height} ${points} ${width},${height}`

  return <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" className="h-9 w-full overflow-visible" aria-hidden="true">
    <polygon points={areaPoints} fill={color} opacity="0.12" />
    <polyline points={points} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
}
