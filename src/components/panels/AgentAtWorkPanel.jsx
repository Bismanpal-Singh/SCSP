import React, { useEffect, useMemo, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import Button from '../Button'
import NarrationLine from './AgentAtWorkPanel/NarrationLine'
import { narrateFinal, narrateIteration, narrationTone } from './AgentAtWorkPanel/narrate'

const TYPE_DELAY_MS = 30
const MAX_VISIBLE_LINES = 6

function buildScript(iterations, finalCandidate) {
  const lines = []

  iterations.forEach((iteration, index) => {
    if (index > 0) lines.push({ id: `divider-${iteration.num}`, divider: true })
    narrateIteration(iteration, index === 0).forEach((text, lineIndex) => {
      lines.push({
        id: `iter-${iteration.num}-${lineIndex}`,
        text,
        tone: narrationTone(text),
      })
    })
  })

  if (finalCandidate) {
    lines.push({ id: 'final-divider', divider: true })
    narrateFinal(finalCandidate).forEach((text, index) => {
      lines.push({
        id: `final-${index}`,
        text,
        tone: narrationTone(text),
      })
    })
  }

  return lines
}

function WinnerMetric({ label, value }) {
  if (value === undefined || value === null || value === '') return null

  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.035] px-3 py-2">
      <p className="text-[11px] text-white/42">{label}</p>
      <p className="mt-1 font-mono text-sm text-white/88">{value}</p>
    </div>
  )
}

function EmptyState() {
  return (
    <div className="flex h-full flex-col items-center justify-center px-6 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full border border-white/10 bg-white/[0.03] text-white/25">
        <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5">
          <path d="M10.5 17.5a7 7 0 1 1 5-2.06l3.03 3.03" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
          <path d="M9.5 8.5 14 12l-4.5 3.5v-7Z" fill="currentColor" />
        </svg>
      </div>
      <p className="mt-4 max-w-sm text-sm text-white/38">
        Type a hypothesis above and run the agent to see how it works.
      </p>
    </div>
  )
}

export default function AgentAtWorkPanel({
  finalCandidate = null,
  isRunning = false,
  iterations = [],
  onViewReasoning,
  onViewResults,
}) {
  const [visibleLines, setVisibleLines] = useState([])
  const [completedLineIds, setCompletedLineIds] = useState(new Set())
  const script = useMemo(() => buildScript(iterations, finalCandidate), [iterations, finalCandidate])
  const latestLine = visibleLines[visibleLines.length - 1]
  const isComplete = Boolean(finalCandidate) && !isRunning

  useEffect(() => {
    setVisibleLines((current) => {
      const currentIds = current.map((line) => line.id)
      const scriptIds = script.map((line) => line.id)
      const isPrefix = currentIds.every((id, index) => id === scriptIds[index])

      if (!isPrefix || current.length > script.length) {
        setCompletedLineIds(new Set())
        return []
      }

      return current
    })
  }, [script])

  useEffect(() => {
    if (visibleLines.length === 0 && script.length > 0) {
      setVisibleLines([{ ...script[0], renderedText: '' }])
    }
  }, [script, visibleLines.length])

  useEffect(() => {
    if (visibleLines.length === 0) return undefined

    const activeIndex = visibleLines.length - 1
    const active = visibleLines[activeIndex]
    const target = script[activeIndex]
    if (!active || !target) return undefined

    if (active.divider) {
      if (visibleLines.length < script.length) {
        const id = window.setTimeout(() => {
          setCompletedLineIds((ids) => new Set(ids).add(active.id))
          setVisibleLines((lines) => [...lines, { ...script[lines.length], renderedText: '' }].slice(-MAX_VISIBLE_LINES))
        }, 250)
        return () => window.clearTimeout(id)
      }
      return undefined
    }

    if (active.renderedText.length < target.text.length) {
      const id = window.setTimeout(() => {
        setVisibleLines((lines) => {
          const next = [...lines]
          const last = next[next.length - 1]
          const lineTarget = script[activeIndex]
          next[next.length - 1] = {
            ...last,
            renderedText: lineTarget.text.slice(0, last.renderedText.length + 1),
          }
          return next
        })
      }, TYPE_DELAY_MS)
      return () => window.clearTimeout(id)
    }

    if (visibleLines.length < script.length) {
      const id = window.setTimeout(() => {
        setCompletedLineIds((ids) => new Set(ids).add(active.id))
        setVisibleLines((lines) => [...lines, { ...script[activeIndex + 1], renderedText: '' }].slice(-MAX_VISIBLE_LINES))
      }, 450)
      return () => window.clearTimeout(id)
    }

    setCompletedLineIds((ids) => new Set(ids).add(active.id))
    return undefined
  }, [script, visibleLines])

  return (
    <div className="space-y-5 text-left">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <p className="text-sm font-semibold text-white/86">Agent at Work</p>
          <p className="mt-0.5 text-xs text-white/38">A plain-English narration of the search as it runs.</p>
        </div>
        <span
          className={[
            'inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors',
            isComplete
              ? 'border-emerald-300/20 bg-emerald-300/[0.08] text-emerald-100'
              : 'border-cyan-300/20 bg-cyan-300/[0.07] text-cyan-100',
          ].join(' ')}
        >
          <span className={isComplete ? 'text-emerald-300' : 'animate-pulse text-cyan-300'}>
            {isComplete ? '✓' : '●'}
          </span>
          {isComplete ? 'Complete' : 'Agent running...'}
        </span>
      </div>

      <section className="h-[420px] overflow-hidden rounded-2xl border border-white/10 bg-[var(--surface)] p-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
        {script.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="flex h-full flex-col justify-end gap-3">
            <AnimatePresence initial={false}>
              {visibleLines.map((line, index) =>
                line.divider ? (
                  <motion.div
                    key={line.id}
                    layout
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 0.28, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                    transition={{ duration: 0.45 }}
                    className="text-white/22"
                  >
                    ─────────────────────────────────────────────
                  </motion.div>
                ) : (
                  <NarrationLine
                    key={line.id}
                    isActive={index === visibleLines.length - 1 && !completedLineIds.has(line.id)}
                    text={line.renderedText}
                    tone={line.tone}
                  />
                ),
              )}
            </AnimatePresence>
          </div>
        )}
      </section>

      <AnimatePresence>
        {isComplete && finalCandidate && (
          <motion.section
            initial={{ opacity: 0, y: 22 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 12 }}
            transition={{ duration: 0.8, ease: 'easeOut' }}
            className="rounded-2xl border border-emerald-300/15 bg-emerald-300/[0.045] p-5 shadow-[0_0_36px_rgba(74,222,128,0.08)]"
          >
            <p className="text-base font-semibold text-emerald-100">✓ Search complete — found a match</p>

            <div className="mt-4 rounded-xl border border-white/10 bg-black/20 p-4">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="font-mono text-3xl font-bold text-white">{finalCandidate.formula}</p>
                  {finalCandidate.fullName && (
                    <p className="mt-1 text-sm text-white/48">{finalCandidate.fullName}</p>
                  )}
                </div>
                <span className="rounded-full border border-emerald-300/25 bg-emerald-300/[0.08] px-3 py-1 font-mono text-xs text-emerald-100">
                  Score {finalCandidate.score ?? 'n/a'}
                </span>
              </div>

              <div className="mt-4 grid gap-3 sm:grid-cols-3">
                <WinnerMetric label="Magnetic moment" value={finalCandidate.magneticMoment} />
                <WinnerMetric label="Thermal stability" value={finalCandidate.thermalStability} />
                <WinnerMetric label="China dependency" value={finalCandidate.chinaDependency} />
              </div>

              <p className="mt-4 text-sm leading-6 text-white/66">
                Supply chain looks clean: {finalCandidate.supplyChainScore ? `${finalCandidate.supplyChainScore}/100 supply chain score` : 'no major dependency flags surfaced'}.
              </p>
            </div>

            <div className="mt-5 flex flex-wrap items-center gap-3">
              <Button onClick={onViewResults} size="sm">
                View Full Results →
              </Button>
              <button
                type="button"
                onClick={onViewReasoning}
                className="text-sm font-medium text-cyan-200/80 transition hover:text-cyan-100"
              >
                See agent&apos;s reasoning →
              </button>
            </div>
          </motion.section>
        )}
      </AnimatePresence>
    </div>
  )
}
