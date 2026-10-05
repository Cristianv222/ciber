import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import { useTheme } from '../theme/ThemeContext.jsx'

// Fondo de nube de puntos monocroma (Three.js puro, sin React-Three-Fiber).
export default function ThreeBackground() {
  const mountRef = useRef(null)
  const { theme } = useTheme()

  useEffect(() => {
    const mount = mountRef.current
    if (!mount) return

    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(55, mount.clientWidth / mount.clientHeight, 0.1, 100)
    camera.position.z = 16

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setSize(mount.clientWidth, mount.clientHeight)
    mount.appendChild(renderer.domElement)

    const count = 1600
    const positions = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      const r = 7 + Math.random() * 7
      const theta = Math.random() * Math.PI * 2
      const phi = Math.acos(2 * Math.random() - 1)
      positions[i * 3] = r * Math.sin(phi) * Math.cos(theta)
      positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta)
      positions[i * 3 + 2] = r * Math.cos(phi)
    }
    const geom = new THREE.BufferGeometry()
    geom.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    const mat = new THREE.PointsMaterial({
      size: 0.045,
      color: new THREE.Color(theme === 'dark' ? '#5a5a66' : '#b8b8c0'),
      transparent: true,
      opacity: 0.5,
      sizeAttenuation: true,
      depthWrite: false,
    })
    const points = new THREE.Points(geom, mat)
    scene.add(points)

    let raf
    const clock = new THREE.Clock()
    const animate = () => {
      const d = clock.getDelta()
      points.rotation.y += d * 0.03
      points.rotation.x += d * 0.008
      renderer.render(scene, camera)
      raf = requestAnimationFrame(animate)
    }
    animate()

    const onResize = () => {
      if (!mount) return
      camera.aspect = mount.clientWidth / mount.clientHeight
      camera.updateProjectionMatrix()
      renderer.setSize(mount.clientWidth, mount.clientHeight)
    }
    window.addEventListener('resize', onResize)

    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('resize', onResize)
      geom.dispose()
      mat.dispose()
      renderer.dispose()
      if (renderer.domElement.parentNode) renderer.domElement.parentNode.removeChild(renderer.domElement)
    }
  }, [theme])

  return <div ref={mountRef} className="absolute inset-0 -z-10" />
}
