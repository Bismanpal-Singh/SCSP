import React, { useEffect, useRef, useState } from 'react'

const easeOut = (t) => 1 - (1 - t) ** 2

/**
 * Drives monospaced “live” numbers during the pipeline. Targets ease with each step.
 */
export default function MetricsPanel({ activeStep }) {
  const fromRef = useRef({ candidates: 0, iterations: 0, score: 0.42 })
  const [display, setDisplay] = useState({ candidates: 0, iterations: 0, score: 0.42 })

  useEffect(() => {
    const targets = {
      candidates: 120 + activeStep * 100 + 24,
      iterations: activeStep + 1,
      score: Math.min(0.95, 0.48 + activeStep * 0.1),
    }
    const start = { ...fromRef.current }
    const t0 = performance.now()
    const duration = 500

    function frame(now) {
      const u = Math.min(1, (now - t0) / duration)
      const e = easeOut(u)
      const next = {
        candidates: Math.round(start.candidates + (targets.candidates - start.candidates) * e),
        iterations: Math.round(start.iterations + (targets.iterations - start.iterations) * e),
        score: start.score + (targets.score - start.score) * e,
      }
      setDisplay(next)
      if (u < 1) {
        requestAnimationFrame(frame)
      } else {
        fromRef.current = { ...next }
      }
    }
    const raf = requestAnimationFrame(frame)
    return () => cancelAnimationFrame(raf)
  }, [activeStep])

  return (
    <div className="w-full max-w-sm rounded-xl border border-violet-500/20 bg-black/25 px-4 py-3 font-mono text-[11px] shadow-[0_0_24px_rgba(139,92,246,0.12),inset_0_1px_0_rgba(255,255,255,0.05)] backdrop-blur-md sm:max-w-xs sm:px-5 sm:text-xs">
      <p className="mb-2 border-b border-white/10 pb-2 text-[9px] uppercase tracking-[0.2em] text-violet-400/90">
        Live metrics
      </p>
      <ul className="space-y-1.5 text-white/85">
        <li className="flex justify-between gap-4">
          <span className="text-white/45">Candidates evaluated</span>
          <span className="text-emerald-300/90 tabular-nums">{display.candidates}</span>
        </li>
        <li className="flex justify-between gap-4">
          <span className="text-white/45">Iterations</span>
          <span className="text-violet-200/90 tabular-nums">{display.iterations}</span>
        </li>
        <li className="flex justify-between gap-4">
          <span className="text-white/45">Best score</span>
          <span className="text-fuchsia-200/90 tabular-nums">{display.score.toFixed(3)}</span>
        </li>
      </ul>
    </div>
  )
}
