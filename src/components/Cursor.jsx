import React, { useEffect, useRef, useState } from 'react'

const CORE_SIZE = 7
const AMBIENT_SIZE = 180
const MAGNET_MAX = 6

const interactiveSelector = 'a, button, input, textarea, select, [role="button"], [data-magnetic="true"]'
const magneticSelector = '[data-magnetic="true"]'

function lerp(from, to, amount) {
  return from + (to - from) * amount
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value))
}

/**
 * Premium custom cursor: precise core dot and a slower ambient glow.
 * Motion uses a single requestAnimationFrame loop to avoid
 * mousemove-driven renders. Magnetic elements are moved with CSS `translate`
 * so existing hover scale transforms still work.
 */
export default function Cursor() {
  const coreRef = useRef(null)
  const ambientRef = useRef(null)
  const rafRef = useRef(0)
  const target = useRef({ x: -500, y: -500 })
  const core = useRef({ x: -500, y: -500 })
  const ambient = useRef({ x: -500, y: -500 })
  const state = useRef({ active: false, visible: false, clicking: false })
  const magnetEl = useRef(null)
  const [enabled, setEnabled] = useState(false)

  useEffect(() => {
    const canUseCustomCursor =
      window.matchMedia('(pointer: fine)').matches &&
      !window.matchMedia('(prefers-reduced-motion: reduce)').matches

    if (!canUseCustomCursor) return undefined

    setEnabled(true)
    document.documentElement.classList.add('mantle-custom-cursor')

    function resetMagnet() {
      if (!magnetEl.current) return
      magnetEl.current.style.translate = '0px 0px'
      magnetEl.current = null
    }

    function applyMagnet(e) {
      const candidate = e.target?.closest?.(magneticSelector)
      if (!candidate) {
        resetMagnet()
        return
      }

      if (magnetEl.current && magnetEl.current !== candidate) {
        magnetEl.current.style.translate = '0px 0px'
      }

      const rect = candidate.getBoundingClientRect()
      const dx = clamp((e.clientX - (rect.left + rect.width / 2)) * 0.08, -MAGNET_MAX, MAGNET_MAX)
      const dy = clamp((e.clientY - (rect.top + rect.height / 2)) * 0.08, -MAGNET_MAX, MAGNET_MAX)

      candidate.style.translate = `${dx}px ${dy}px`
      candidate.style.transition = 'translate 180ms cubic-bezier(0.22, 1, 0.36, 1)'
      magnetEl.current = candidate
    }

    function onMove(e) {
      target.current = { x: e.clientX, y: e.clientY }
      state.current.visible = true
      state.current.active = Boolean(e.target?.closest?.(interactiveSelector))
      applyMagnet(e)
    }

    function onDown() {
      state.current.clicking = true
      window.setTimeout(() => {
        state.current.clicking = false
      }, 160)
    }

    function onLeave() {
      state.current.visible = false
      state.current.active = false
      resetMagnet()
    }

    function tick() {
      const t = target.current
      core.current.x = lerp(core.current.x, t.x, 0.62)
      core.current.y = lerp(core.current.y, t.y, 0.62)
      ambient.current.x = lerp(ambient.current.x, t.x, 0.075)
      ambient.current.y = lerp(ambient.current.y, t.y, 0.075)

      const visible = state.current.visible
      const active = state.current.active
      const clicking = state.current.clicking

      if (coreRef.current) {
        const scale = clicking ? 0.78 : active ? 1.08 : 1
        coreRef.current.style.opacity = visible ? '1' : '0'
        coreRef.current.style.transform = `translate3d(${core.current.x - CORE_SIZE / 2}px, ${
          core.current.y - CORE_SIZE / 2
        }px, 0) scale(${scale})`
      }

      if (ambientRef.current) {
        const glowScale = active ? 1.18 : 1
        ambientRef.current.style.opacity = visible ? (active ? '0.12' : '0.07') : '0'
        ambientRef.current.style.transform = `translate3d(${ambient.current.x - AMBIENT_SIZE / 2}px, ${
          ambient.current.y - AMBIENT_SIZE / 2
        }px, 0) scale(${glowScale})`
      }

      rafRef.current = requestAnimationFrame(tick)
    }

    window.addEventListener('mousemove', onMove, { passive: true })
    window.addEventListener('mousedown', onDown)
    window.addEventListener('mouseleave', onLeave)
    rafRef.current = requestAnimationFrame(tick)

    return () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mousedown', onDown)
      window.removeEventListener('mouseleave', onLeave)
      cancelAnimationFrame(rafRef.current)
      resetMagnet()
      document.documentElement.classList.remove('mantle-custom-cursor')
    }
  }, [])

  if (!enabled) return null

  return (
    <>
      <style>{`
        .mantle-custom-cursor,
        .mantle-custom-cursor * {
          cursor: none !important;
        }
      `}</style>
      <div
        ref={ambientRef}
        className="pointer-events-none fixed left-0 top-0 z-[65] h-[180px] w-[180px] rounded-full bg-[radial-gradient(circle,rgba(139,92,246,0.75)_0%,rgba(99,102,241,0.18)_42%,transparent_72%)] blur-3xl mix-blend-screen transition-opacity duration-300"
        style={{ opacity: 0, willChange: 'transform, opacity' }}
        aria-hidden
      />
      <div
        ref={coreRef}
        className="pointer-events-none fixed left-0 top-0 z-[75] h-[7px] w-[7px] rounded-full bg-violet-50 shadow-[0_0_12px_rgba(196,181,253,0.9)]"
        style={{ opacity: 0, willChange: 'transform, opacity' }}
        aria-hidden
      />
    </>
  )
}
