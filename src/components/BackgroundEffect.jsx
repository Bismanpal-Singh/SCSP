import React, { useCallback, useEffect, useRef, useState } from 'react'

/**
 * Parallax: we map cursor position to small translate offsets on layered decorations.
 * Values are clamped and smoothed so motion feels premium, not gimmicky.
 */
const LAYER_STRENGTH = { mesh: 12, grid: 18, orb: 22 }

export default function BackgroundEffect() {
  const raf = useRef(0)
  const target = useRef({ x: 0, y: 0 })
  const current = useRef({ x: 0, y: 0 })

  const [styleMesh, setStyleMesh] = useState({ transform: 'translate3d(0px,0px,0)' })
  const [styleGrid, setStyleGrid] = useState({ transform: 'translate3d(0px,0px,0)' })
  const [styleOrb, setStyleOrb] = useState({ transform: 'translate3d(0px,0px,0)' })

  const onMove = useCallback((e) => {
    const cx = window.innerWidth / 2
    const cy = window.innerHeight / 2
    const nx = (e.clientX - cx) / cx
    const ny = (e.clientY - cy) / cy
    target.current = { x: nx, y: ny }
  }, [])

  useEffect(() => {
    const tick = () => {
      const t = target.current
      const c = current.current
      const lerp = 0.06
      c.x += (t.x - c.x) * lerp
      c.y += (t.y - c.y) * lerp

      setStyleMesh({
        transform: `translate3d(${c.x * -LAYER_STRENGTH.mesh}px, ${c.y * -LAYER_STRENGTH.mesh}px, 0)`,
      })
      setStyleGrid({
        transform: `translate3d(${c.x * LAYER_STRENGTH.grid}px, ${c.y * LAYER_STRENGTH.grid}px, 0)`,
      })
      setStyleOrb({
        transform: `translate3d(${c.x * -LAYER_STRENGTH.orb}px, ${c.y * -LAYER_STRENGTH.orb}px, 0)`,
      })

      raf.current = requestAnimationFrame(tick)
    }
    raf.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf.current)
  }, [])

  useEffect(() => {
    window.addEventListener('mousemove', onMove, { passive: true })
    return () => window.removeEventListener('mousemove', onMove)
  }, [onMove])

  return (
    <div
      className="pointer-events-none fixed inset-0 z-0 overflow-hidden bg-mantle-bg"
      aria-hidden
    >
      {/* Base purple–indigo vignette */}
      <div
        className="absolute inset-0 opacity-80"
        style={{
          background:
            'radial-gradient(ellipse 80% 55% at 50% 0%, rgba(139, 92, 246, 0.14) 0%, transparent 55%), radial-gradient(ellipse 60% 40% at 80% 100%, rgba(99, 102, 241, 0.08) 0%, transparent 50%), radial-gradient(ellipse 50% 30% at 10% 90%, rgba(79, 70, 229, 0.06) 0%, transparent 45%)',
        }}
      />

      {/* Crystalline mesh — large geometric lines */}
      <div
        className="absolute inset-[-15%] opacity-[0.12] transition-transform duration-300 will-change-transform"
        style={styleMesh}
      >
        <svg className="h-full w-full" preserveAspectRatio="xMidYMid slice">
          <defs>
            <pattern id="lattice" width="64" height="64" patternUnits="userSpaceOnUse">
              <path
                d="M0 32 L32 0 L64 32 L32 64 Z"
                fill="none"
                stroke="rgba(139,92,246,0.45)"
                strokeWidth="0.5"
              />
              <path d="M32 0 V64 M0 32 H64" stroke="rgba(139,92,246,0.2)" strokeWidth="0.35" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#lattice)" />
        </svg>
      </div>

      {/* Finer grid overlay */}
      <div
        className="absolute inset-0 opacity-[0.06] will-change-transform"
        style={{
          ...styleGrid,
          backgroundImage: `
            linear-gradient(rgba(139,92,246,0.4) 1px, transparent 1px),
            linear-gradient(90deg, rgba(139,92,246,0.35) 1px, transparent 1px)
          `,
          backgroundSize: '48px 48px',
        }}
      />

      {/* Soft orbs — depth without noise */}
      <div
        className="absolute -left-[20%] top-1/4 h-[420px] w-[420px] rounded-full blur-[100px] will-change-transform"
        style={{
          ...styleOrb,
          background: 'radial-gradient(circle, rgba(139, 92, 246, 0.18) 0%, transparent 70%)',
        }}
      />
      <div
        className="absolute -right-[15%] bottom-[10%] h-[380px] w-[380px] rounded-full blur-[90px] opacity-70 will-change-transform"
        style={{
          transform: styleOrb.transform,
          background: 'radial-gradient(circle, rgba(99, 102, 241, 0.12) 0%, transparent 70%)',
        }}
      />
    </div>
  )
}
