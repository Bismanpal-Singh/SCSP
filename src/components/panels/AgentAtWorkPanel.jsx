import React, { useEffect, useMemo, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import Button from '../Button'
import NarrationLine from './AgentAtWorkPanel/NarrationLine'
import { narrateFinal, narrateIteration, narrationTone } from './AgentAtWorkPanel/narrate'
import MaterialLink from '../MaterialLink'

const TYPE_DELAY_MS = 30
const MAX_VISIBLE_LINES = 6
const MAX_SCRIPT_LINES = 10

function buildScript(iterations, finalCandidate) {
  const base = [
    {
      id: 'start-reading',
      text: 'Reading your hypothesis...',
      tone: 'default',
    },
    {
      id: 'start-database',
      text: 'Searching 150,000 materials in the Materials Project database...',
      tone: 'default',
    },
  ]

  const lines = [...base]
  iterations.forEach((iteration, index) => {
    if (lines.length >= MAX_SCRIPT_LINES - (finalCandidate ? 1 : 0)) return
    const iterationLines = narrateIteration(iteration, index === 0, iterations[index - 1]).slice(0, 2)
    iterationLines.forEach((text, lineIndex) => {
      if (lines.length >= MAX_SCRIPT_LINES - (finalCandidate ? 1 : 0)) return
      lines.push({
        id: `iter-${iteration.num}-${lineIndex}`,
        text,
        tone: narrationTone(text),
      })
    })
  })

  if (finalCandidate) {
    narrateFinal(finalCandidate).forEach((text, index) => {
      if (lines.length < MAX_SCRIPT_LINES) {
        lines.push({
          id: `final-${index}`,
          text,
          tone: narrationTone(text),
        })
      }
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

function ResultsCard({ finalCandidate, onViewReasoning, onViewResults }) {
  return (
    <motion.div
      key="results"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.6, ease: 'easeOut' }}
      className="flex h-full flex-col justify-center"
    >
      <div className="rounded-2xl border border-emerald-300/15 bg-emerald-300/[0.045] p-5 shadow-[0_0_36px_rgba(74,222,128,0.08)]">
        <p className="text-base font-semibold text-emerald-100">✓ Search complete — found a match</p>

        <div className="mt-4 rounded-xl border border-white/10 bg-black/20 p-4">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="font-mono text-3xl font-bold text-white">
                <MaterialLink mpId={finalCandidate.mpId} formula={finalCandidate.formula}>
                  {finalCandidate.formula}
                </MaterialLink>
              </p>
              {finalCandidate.fullName && (
                <p className="mt-1 text-sm text-white/48">{finalCandidate.fullName}</p>
              )}
            </div>
            <span className="rounded-full border border-emerald-300/25 bg-emerald-300/[0.08] px-3 py-1 font-mono text-xs text-emerald-100">
              Score {finalCandidate.score ?? 'n/a'}
            </span>
          </div>

          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <WinnerMetric label="Thermal stability" value={finalCandidate.thermalStability} />
            <WinnerMetric label="China dependency" value={finalCandidate.chinaDependency} />
          </div>

          <p className="mt-4 text-sm leading-6 text-white/66">
            Convergence notes indicate no major dependency flags surfaced.
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
      </div>
    </motion.div>
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
  const [scriptCursor, setScriptCursor] = useState(0)
  const [showResults, setShowResults] = useState(false)
  const script = useMemo(() => buildScript(iterations, finalCandidate), [iterations, finalCandidate])
  const formulaMpIdMap = useMemo(() => {
    const map = {}
    iterations.forEach((iteration) => {
      if (iteration?.bestFormula && iteration?.bestCandidate?.mpId) {
        map[iteration.bestFormula] = iteration.bestCandidate.mpId
      }
    })
    if (finalCandidate?.formula && finalCandidate?.mpId) {
      map[finalCandidate.formula] = finalCandidate.mpId
    }
    return map
  }, [finalCandidate, iterations])
  const isComplete = Boolean(finalCandidate) && !isRunning
  const finalLineId = script.at(-1)?.id

  useEffect(() => {
    if (script.length === 0) {
      setVisibleLines([])
      setCompletedLineIds(new Set())
      setScriptCursor(0)
      setShowResults(false)
      return
    }

    const scriptIds = new Set(script.map((line) => line.id))
    const hasStaleLine = visibleLines.some((line) => !scriptIds.has(line.id))

    if (hasStaleLine) {
      setVisibleLines([])
      setCompletedLineIds(new Set())
      setScriptCursor(0)
      setShowResults(false)
    }
  }, [script])

  useEffect(() => {
    if (!isComplete) {
      setShowResults(false)
      return undefined
    }

    // Keep narration visible until the final scripted line has finished typing.
    if (!finalLineId || !completedLineIds.has(finalLineId)) {
      return undefined
    }

    const id = window.setTimeout(() => setShowResults(true), 550)
    return () => window.clearTimeout(id)
  }, [completedLineIds, finalLineId, isComplete])

  useEffect(() => {
    if (visibleLines.length === 0 && script.length > 0 && scriptCursor === 0) {
      setVisibleLines([{ ...script[0], renderedText: '' }])
      setScriptCursor(1)
    }
  }, [script, scriptCursor, visibleLines.length])

  useEffect(() => {
    if (visibleLines.length === 0) return undefined

    const active = visibleLines[visibleLines.length - 1]
    if (!active) return undefined

    if (active.divider) {
      if (scriptCursor < script.length) {
        const id = window.setTimeout(() => {
          setCompletedLineIds((ids) => new Set(ids).add(active.id))
          setVisibleLines((lines) => [...lines, { ...script[scriptCursor], renderedText: '' }].slice(-MAX_VISIBLE_LINES))
          setScriptCursor((cursor) => cursor + 1)
        }, 250)
        return () => window.clearTimeout(id)
      }
      return undefined
    }

    if (active.renderedText.length < active.text.length) {
      const id = window.setTimeout(() => {
        setVisibleLines((lines) => {
          const next = [...lines]
          const last = next[next.length - 1]
          next[next.length - 1] = {
            ...last,
            renderedText: last.text.slice(0, last.renderedText.length + 1),
          }
          return next
        })
      }, TYPE_DELAY_MS)
      return () => window.clearTimeout(id)
    }

    if (scriptCursor < script.length) {
      const id = window.setTimeout(() => {
        setCompletedLineIds((ids) => new Set(ids).add(active.id))
        setVisibleLines((lines) => [...lines, { ...script[scriptCursor], renderedText: '' }].slice(-MAX_VISIBLE_LINES))
        setScriptCursor((cursor) => cursor + 1)
      }, 450)
      return () => window.clearTimeout(id)
    }

    setCompletedLineIds((ids) => new Set(ids).add(active.id))
    return undefined
  }, [script, scriptCursor, visibleLines])

  return (
    <div className="w-full space-y-5 text-left">
      <div className="mb-3">
        <div>
          <p className="text-sm font-semibold text-white/86">Agent at Work</p>
        </div>
      </div>

      <section className="relative h-[420px] overflow-hidden rounded-2xl border border-white/10 bg-[var(--surface)] px-8 py-7 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
        <span
          className={[
            'absolute right-4 top-4 inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors',
            isComplete
              ? 'border-emerald-300/20 bg-emerald-300/[0.08] text-emerald-100'
              : 'border-cyan-300/20 bg-cyan-300/[0.07] text-cyan-100',
          ].join(' ')}
        >
          <span className={isComplete ? 'text-emerald-300' : 'animate-pulse text-cyan-300'}>
            {isComplete ? '✓' : '●'}
          </span>
          {isComplete ? 'Search complete' : 'Agent running'}
        </span>
        <AnimatePresence mode="wait" initial={false}>
          {showResults && finalCandidate ? (
            <ResultsCard
              finalCandidate={finalCandidate}
              onViewReasoning={onViewReasoning}
              onViewResults={onViewResults}
            />
          ) : script.length === 0 ? (
            <motion.div
              key="empty"
              className="h-full"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.6 }}
            >
              <EmptyState />
            </motion.div>
          ) : (
            <motion.div
              key="narration"
              className="h-full overflow-y-auto pr-28"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.6 }}
            >
              <div className="flex flex-col justify-start gap-3">
                <AnimatePresence initial={false}>
                  {visibleLines.map((line, index) => (
                    <NarrationLine
                      key={line.id}
                      isActive={index === visibleLines.length - 1 && !completedLineIds.has(line.id)}
                      text={line.renderedText}
                      tone={line.tone}
                      formulaMpIdMap={formulaMpIdMap}
                    />
                  ))}
                </AnimatePresence>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </section>
    </div>
  )
}
