import { useEffect, useRef, useState } from 'react'
import Globe from 'react-globe.gl'

// Globo terráqueo 3D con arcos animados desde cada origen de ataque hacia el honeypot.
export default function AttackGlobe({ points = [], target }) {
  const wrapRef = useRef(null)
  const globeRef = useRef(null)
  const [width, setWidth] = useState(640)
  const height = 460

  useEffect(() => {
    const el = wrapRef.current
    if (!el) return
    const ro = new ResizeObserver(() => setWidth(el.clientWidth))
    ro.observe(el)
    setWidth(el.clientWidth)
    return () => ro.disconnect()
  }, [])

  useEffect(() => {
    const g = globeRef.current
    if (!g || !target) return
    const controls = g.controls()
    controls.autoRotate = true
    controls.autoRotateSpeed = 0.45
    controls.enableZoom = true
    g.pointOfView({ lat: 15, lng: -50, altitude: 2.3 }, 0)
  }, [target])

  if (!target) return null

  const arcs = points.map((p) => ({
    startLat: p.lat, startLng: p.lon,
    endLat: target.lat, endLng: target.lon,
    total: p.total, country: p.country,
  }))

  const pts = [
    ...points.map((p) => ({
      lat: p.lat, lng: p.lon,
      size: Math.min(0.08 + p.total * 0.02, 0.6),
      color: '#ef4444',
      label: `${p.country || 'Desconocido'}${p.city ? ' · ' + p.city : ''} — ${p.total} ataques`,
    })),
    { lat: target.lat, lng: target.lon, size: 0.45, color: '#22c55e', label: target.label },
  ]

  return (
    <div ref={wrapRef} style={{ height }}>
      <Globe
        ref={globeRef}
        width={width}
        height={height}
        globeImageUrl="/earth-dark.jpg"
        bumpImageUrl="/earth-topology.png"
        backgroundColor="rgba(0,0,0,0)"
        atmosphereColor="#6b7a8d"
        atmosphereAltitude={0.16}
        arcsData={arcs}
        arcStartLat="startLat"
        arcStartLng="startLng"
        arcEndLat="endLat"
        arcEndLng="endLng"
        arcColor={() => ['rgba(239,68,68,0.08)', 'rgba(239,68,68,0.95)']}
        arcStroke={0.5}
        arcDashLength={0.45}
        arcDashGap={1}
        arcDashInitialGap={() => Math.random()}
        arcDashAnimateTime={1800}
        arcsTransitionDuration={0}
        pointsData={pts}
        pointLat="lat"
        pointLng="lng"
        pointColor="color"
        pointAltitude="size"
        pointRadius={0.28}
        pointLabel="label"
        pointsMerge={false}
      />
    </div>
  )
}
