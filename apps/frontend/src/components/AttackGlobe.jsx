import { useEffect, useMemo, useRef, useState } from 'react'
import Globe from 'react-globe.gl'
import * as THREE from 'three'

// Paleta de colores distintos por país (rayos multicolor)
const PALETTE = [
  '#ef4444', '#f59e0b', '#eab308', '#84cc16', '#22c55e', '#14b8a6',
  '#06b6d4', '#38bdf8', '#a78bfa', '#d946ef', '#ec4899', '#fb7185',
  '#f97316', '#a3e635', '#2dd4bf', '#fbbf24',
]
const hexA = (hex, a) => {
  const n = parseInt(hex.slice(1), 16)
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`
}

// Globo 3D "live map" a pantalla completa. El mundo siempre gira; cada país de
// origen (geolocalizado por GeoIP) lanza un RAYO de su propio color que fluye
// hacia el único punto de la red monitoreada (Ecuador), que queda brillando.
// Clic en un origen o su rayo → onSelect(point) con los ataques reales.
export default function AttackGlobe({ points = [], target, onSelect, theme = 'dark' }) {
  const wrapRef = useRef(null)
  const globeRef = useRef(null)
  const [size, setSize] = useState({ w: 800, h: 600 })
  const light = theme === 'light'

  useEffect(() => {
    const el = wrapRef.current
    if (!el) return
    const measure = () => setSize({ w: el.clientWidth, h: el.clientHeight })
    const ro = new ResizeObserver(measure)
    ro.observe(el)
    measure()
    return () => ro.disconnect()
  }, [])

  // Cámara, auto-rotación y realce del material
  useEffect(() => {
    const g = globeRef.current
    if (!g || !target) return
    const controls = g.controls()
    controls.autoRotate = true
    controls.autoRotateSpeed = 0.5
    controls.enableZoom = true
    controls.minDistance = 180
    controls.maxDistance = 600
    g.pointOfView({ lat: 8, lng: -60, altitude: 2.1 }, 0)

    const mat = g.globeMaterial && g.globeMaterial()
    if (mat) {
      mat.bumpScale = 6
      if (mat.emissive) {
        mat.emissive.set(light ? '#22333d' : '#101826')
        mat.emissiveIntensity = light ? 0.35 : 1
      }
      mat.needsUpdate = true
    }
  }, [target, size.w, light])

  // Punto destino BRILLANTE: sprite con glow aditivo que late sobre Ecuador
  useEffect(() => {
    const g = globeRef.current
    if (!g || !target || !g.getCoords) return
    let sprite, raf, stopped = false
    const cv = document.createElement('canvas')
    cv.width = cv.height = 128
    const ctx = cv.getContext('2d')
    const grd = ctx.createRadialGradient(64, 64, 0, 64, 64, 64)
    grd.addColorStop(0, 'rgba(90,255,170,0.95)')
    grd.addColorStop(0.25, 'rgba(34,197,94,0.6)')
    grd.addColorStop(1, 'rgba(34,197,94,0)')
    ctx.fillStyle = grd
    ctx.fillRect(0, 0, 128, 128)
    const tex = new THREE.CanvasTexture(cv)
    const smat = new THREE.SpriteMaterial({ map: tex, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending })
    sprite = new THREE.Sprite(smat)
    const c = g.getCoords(target.lat, target.lon, 0.02)
    sprite.position.set(c.x, c.y, c.z)
    g.scene().add(sprite)
    const t0 = performance.now()
    const base = 16
    const pulse = () => {
      if (stopped) return
      const k = 1 + 0.22 * Math.sin((performance.now() - t0) / 480)
      sprite.scale.set(base * k, base * k, 1)
      raf = requestAnimationFrame(pulse)
    }
    pulse()
    return () => {
      stopped = true
      if (raf) cancelAnimationFrame(raf)
      if (g.scene) g.scene().remove(sprite)
      smat.dispose(); tex.dispose()
    }
  }, [target, size.w])

  // Arcos (rayos) persistentes: uno por origen, color propio del país, dash
  // animado y escalonado = flujo continuo hacia el objetivo, sin parpadeo.
  const arcs = useMemo(() => {
    if (!target) return []
    return points.map((p, i) => ({
      id: `arc-${i}`,
      startLat: p.lat, startLng: p.lon,
      endLat: target.lat, endLng: target.lon,
      color: p.internal ? '#94a3b8' : PALETTE[i % PALETTE.length],
      raw: p,
      dash0: Math.random(),
      animTime: 2600 + Math.random() * 1800,
    }))
  }, [points, target])

  // Anillos pulsantes: radar sobre el objetivo + marcador de color en cada origen
  const ringsData = useMemo(() => {
    if (!target) return []
    const r = [{ id: 'radar', lat: target.lat, lng: target.lon, color: '#22c55e', maxR: 5.5, speed: 3, period: 1000, a: 0.5 }]
    points.forEach((p, i) => r.push({
      id: `o-${i}`, lat: p.lat, lng: p.lon,
      color: p.internal ? '#94a3b8' : PALETTE[i % PALETTE.length], maxR: 2.2, speed: 2.6,
      period: 1500 + Math.random() * 1700, a: 0.5,
    }))
    return r
  }, [points, target])

  // Etiquetas de país (una por país, en su punto de mayor actividad) + objetivo
  const labelsData = useMemo(() => {
    if (!target) return []
    const best = {}
    points.forEach((p) => {
      const c = p.country || p.city || '—'
      if (!best[c] || p.total > best[c].total) best[c] = p
    })
    const arr = Object.values(best).map((p) => ({
      lat: p.lat, lng: p.lon, text: (p.country || p.city || '').toUpperCase(), raw: p, isTarget: false,
    }))
    arr.push({ lat: target.lat, lng: target.lon, text: (target.label || '').toUpperCase(), isTarget: true })
    return arr
  }, [points, target])

  if (!target) return null

  const pts = [
    ...points.map((p, i) => ({
      lat: p.lat, lng: p.lon,
      radius: Math.min(0.28 + p.total * 0.02, 0.9),
      color: p.internal ? '#94a3b8' : PALETTE[i % PALETTE.length], raw: p,
      label: `${p.country || 'Desconocido'}${p.city ? ' · ' + p.city : ''} — ${p.total} ataques${p.max_cvss ? ' · CVSS ' + p.max_cvss : ''}`,
    })),
    { lat: target.lat, lng: target.lon, radius: 0.5, color: '#22c55e', raw: null, label: target.label },
  ]

  const handlePoint = (pt) => { if (pt && pt.raw && onSelect) onSelect(pt.raw) }
  const handleArc = (ar) => { if (ar && ar.raw && onSelect) onSelect(ar.raw) }

  return (
    <div ref={wrapRef} style={{ width: '100%', height: '100%' }}>
      <Globe
        ref={globeRef}
        width={size.w}
        height={size.h}
        globeImageUrl={light ? '/earth-blue-marble.jpg' : '/earth-night.jpg'}
        bumpImageUrl="/earth-topology.png"
        backgroundColor="rgba(0,0,0,0)"
        atmosphereColor={light ? '#a7c4d1' : '#9aa4b2'}
        atmosphereAltitude={0.28}
        arcsData={arcs}
        arcStartLat="startLat"
        arcStartLng="startLng"
        arcEndLat="endLat"
        arcEndLng="endLng"
        arcColor={(d) => [hexA(d.color, 0), d.color]}
        arcStroke={0.26}
        arcCurveResolution={64}
        arcAltitudeAutoScale={0.42}
        arcDashLength={0.4}
        arcDashGap={0.5}
        arcDashInitialGap={(d) => d.dash0}
        arcDashAnimateTime={(d) => d.animTime}
        arcsTransitionDuration={0}
        onArcClick={handleArc}
        ringsData={ringsData}
        ringLat="lat"
        ringLng="lng"
        ringColor={(d) => (t) => hexA(d.color, d.a * (1 - t))}
        ringMaxRadius={(d) => d.maxR}
        ringPropagationSpeed={(d) => d.speed}
        ringRepeatPeriod={(d) => d.period}
        labelsData={labelsData}
        labelLat="lat"
        labelLng="lng"
        labelText="text"
        labelSize={(d) => (d.isTarget ? 0.9 : 0.58)}
        labelColor={(d) => (d.isTarget ? 'rgba(90,255,170,0.95)' : (light ? 'rgba(20,32,40,0.82)' : 'rgba(228,238,244,0.72)'))}
        labelResolution={2}
        labelAltitude={0.014}
        labelDotRadius={0}
        labelIncludeDot={false}
        onLabelClick={(l) => { if (l && l.raw && onSelect) onSelect(l.raw) }}
        pointsData={pts}
        pointLat="lat"
        pointLng="lng"
        pointColor="color"
        pointAltitude={0.012}
        pointRadius="radius"
        pointLabel="label"
        pointsMerge={false}
        onPointClick={handlePoint}
        onPointHover={(pt) => { if (wrapRef.current) wrapRef.current.style.cursor = pt && pt.raw ? 'pointer' : 'grab' }}
      />
    </div>
  )
}
