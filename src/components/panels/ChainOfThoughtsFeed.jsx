import React, { useEffect, useMemo, useRef, useState } from 'react'

const TYPE_DELAY_MS = 24

function formatTime(seconds) {
  return String(Math.max(0, seconds)).padStart(2, '0')
}

function splitSentences(text = '') {
  return text
    .split(/(?<=[.!?])\s+/)
    .map((sentence) => sentence.trim())
    .filter(Boolean)
}

function lineClass(tone) {
  if (tone === 'context') return 'text-slate-400/75'
  if (tone === 'reject') return 'text-rose-300/90'
  if (tone === 'pivot') return 'text-cyan-300'
  if (tone === 'success') return 'text-emerald-300'
  if (tone === 'warn') return 'text-amber-300'
  return 'text-white/90'
}

function rejectionLinesForIteration(iteration, decisionLog) {
  return decisionLog
    .filter((entry) => Number(entry.iteration) === Number(iteration.num))
    .filter((entry) => entry.decision !== 'selected')
    .filter((entry) => entry.formula !== iteration.bestFormula)
    .sort((a, b) => Number(a.score || 0) - Number(b.score || 0))
    .slice(0, 3)
    .map((entry) => ({
      icon: '✗',
      tone: 'reject',
      text: `Rejected ${entry.formula} — score ${entry.score ?? 'n/a'} — ${entry.reason}`,
    }))
}

function synthesizedRejections(iteration) {
  const sentences = splitSentences(iteration.interpretation)
  const reasons = sentences.length > 0 ? sentences : ['Candidate family failed one or more target constraints.']

  return reasons.slice(0, 2).map((reason, index) => ({
    icon: '✗',
    tone: 'reject',
    text: `Rejected candidate branch ${index + 1} — ${reason}`,
  }))
}

function buildThoughtLines({
  decisionLog,
  finalCandidate,
  isRunning,
  iterations,
  query,
}) {
  let cursorSeconds = 2
  const lines = []

  iterations.forEach((iteration, index) => {
    const iterationLabel = String(iteration.num ?? index + 1).padStart(2, '0')
    const rejections = rejectionLinesForIteration(iteration, decisionLog)
    const fallbackRejections = rejections.length ? rejections : synthesizedRejections(iteration)

    lines.push({
      id: `search-${iteration.num}`,
      icon: '🔍',
      tone: 'action',
      time: cursorSeconds,
      text:
        index === 0
          ? `Searching Materials Project for candidates matching: ${query || 'submitted hypothesis'}...`
          : `Iteration ${iterationLabel} — searching refined candidate space...`,
    })
    cursorSeconds += 2

    lines.push({
      id: `eval-${iteration.num}`,
      icon: '⚙',
      tone: 'action',
      time: cursorSeconds,
      text: `Evaluated ${iteration.candidatesTested ?? 'multiple'} candidates against core spec constraints.`,
    })
    cursorSeconds += 1

    fallbackRejections.forEach((line, rejectionIndex) => {
      lines.push({
        ...line,
        id: `reject-${iteration.num}-${rejectionIndex}`,
        time: cursorSeconds,
      })
      cursorSeconds += 1
    })

    lines.push({
      id: `best-${iteration.num}`,
      icon: iteration.status === 'converged' ? '✓' : '⚠',
      tone: iteration.status === 'converged' ? 'success' : 'warn',
      time: cursorSeconds,
      text: `Best so far: ${iteration.bestFormula || 'unknown'} — score ${iteration.score ?? 'n/a'} — ${iteration.interpretation}`,
    })
    cursorSeconds += 1

    if (iteration.nextHypothesis) {
      lines.push({
        id: `pivot-${iteration.num}`,
        icon: '→',
        tone: 'pivot',
        time: cursorSeconds,
        text: `Pivoting hypothesis: ${iteration.nextHypothesis}`,
      })
      cursorSeconds += 2
    }

    if (index < iterations.length - 1) {
      lines.push({ id: `divider-${iteration.num}`, divider: true })
    }
  })

  if (!isRunning && finalCandidate && iterations.length > 0) {
    const lastIteration = iterations[iterations.length - 1]
    const totalCandidates = iterations.reduce(
      (total, iteration) => total + Number(iteration.candidatesTested || 0),
      0,
    )

    lines.push({ id: 'final-divider', divider: true })
    lines.push({
      id: 'final-converged',
      icon: '✓',
      tone: 'success',
      time: cursorSeconds,
      text: `CONVERGED at iteration ${lastIteration.num ?? iterations.length}, score ${finalCandidate.score ?? lastIteration.score ?? 'n/a'}`,
    })
    cursorSeconds += 1
    lines.push({
      id: 'final-winner',
      icon: '✓',
      tone: 'success',
      time: cursorSeconds,
      text: `Winner: ${finalCandidate.formula || lastIteration.bestFormula || 'unknown'} — meets all spec axes`,
    })
    cursorSeconds += 1
    lines.push({
      id: 'final-total',
      icon: '→',
      tone: 'context',
      time: cursorSeconds,
      text: `Total candidates evaluated: ${totalCandidates || 'n/a'}  ·  Time: ${cursorSeconds}s`,
    })
  }

  return lines
}

export default function ChainOfThoughtsFeed({
  decisionLog = [],
  finalCandidate = null,
  isRunning = false,
  iterations = [],
  onViewResults,
  query = '',
}) {
  const bottomRef = useRef(null)
  const [renderedLines, setRenderedLines] = useState([])

  const lines = useMemo(
    () => buildThoughtLines({ decisionLog, finalCandidate, isRunning, iterations, query }),
    [decisionLog, finalCandidate, isRunning, iterations, query],
  )

  useEffect(() => {
    const isSamePrefix = renderedLines.every((line, index) => line.id === lines[index]?.id)
    if (!isSamePrefix || renderedLines.length > lines.length) {
      setRenderedLines([])
      return undefined
    }

    const activeLine = renderedLines[renderedLines.length - 1]
    const sourceLine = lines[renderedLines.length - 1]

    if (!activeLine && lines.length > 0) {
      setRenderedLines([{ ...lines[0], renderedText: lines[0].divider ? '' : '' }])
      return undefined
    }

    if (activeLine?.divider) {
      if (renderedLines.length < lines.length) {
        const id = window.setTimeout(() => {
          setRenderedLines((items) => [...items, { ...lines[items.length], renderedText: '' }])
        }, 160)
        return () => window.clearTimeout(id)
      }
      return undefined
    }

    if (activeLine && sourceLine && activeLine.renderedText.length < sourceLine.text.length) {
      const id = window.setTimeout(() => {
        setRenderedLines((items) => {
          const next = [...items]
          const last = next[next.length - 1]
          const target = lines[next.length - 1]
          next[next.length - 1] = {
            ...last,
            renderedText: target.text.slice(0, last.renderedText.length + 1),
          }
          return next
        })
      }, TYPE_DELAY_MS)
      return () => window.clearTimeout(id)
    }

    if (renderedLines.length < lines.length) {
      const id = window.setTimeout(() => {
        setRenderedLines((items) => [...items, { ...lines[items.length], renderedText: '' }])
      }, 180)
      return () => window.clearTimeout(id)
    }

    return undefined
  }, [lines, renderedLines])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: 'end', behavior: 'smooth' })
  }, [renderedLines])

  const complete = !isRunning && finalCandidate

  return (
    <div className="relative overflow-hidden rounded-2xl border border-cyan-300/15 bg-[#060c17] text-left shadow-[0_0_40px_rgba(34,211,238,0.08),inset_0_1px_0_rgba(255,255,255,0.05)]">
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.06]"
        style={{
          backgroundImage:
            'linear-gradient(rgba(255,255,255,0.9) 1px, transparent 1px)',
          backgroundSize: '100% 4px',
        }}
        aria-hidden
      />
      <div className="relative flex items-center justify-between border-b border-white/10 px-4 py-3 font-mono">
        <div>
          <p className="text-[10px] uppercase tracking-[0.22em] text-cyan-200/70">
            Chain of Thoughts
          </p>
          <p className="mt-1 text-xs text-slate-400">Live agent reasoning stream</p>
        </div>
        <span className="rounded-full border border-cyan-300/20 bg-cyan-300/[0.06] px-3 py-1 text-[10px] uppercase tracking-[0.16em] text-cyan-100/70">
          {isRunning ? 'Streaming' : complete ? 'Complete' : 'Standby'}
        </span>
      </div>

      <div className="relative h-[480px] overflow-y-auto px-4 py-4 font-mono text-[13px] leading-[1.7]">
        {renderedLines.length === 0 && (
          <p className="text-slate-400/75">
            {isRunning ? 'Awaiting first agent iteration...' : 'No thoughts streamed yet.'}
          </p>
        )}

        <div className="space-y-1.5">
          {renderedLines.map((line) =>
            line.divider ? (
              <div key={line.id} className="py-2 text-cyan-100/18">
                ─────────────────────────────────────────────
              </div>
            ) : (
              <div key={line.id} className={`grid grid-cols-[52px_22px_1fr] gap-2 ${lineClass(line.tone)}`}>
                <span className="text-slate-500">[00:{formatTime(line.time)}]</span>
                <span>{line.icon}</span>
                <span>{line.renderedText}</span>
              </div>
            ),
          )}
          {isRunning && (
            <div className="ml-[74px] mt-2 h-4 w-2 animate-pulse bg-cyan-300 shadow-[0_0_16px_rgba(34,211,238,0.75)]" />
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      {complete && (
        <div className="relative border-t border-cyan-300/10 px-4 py-4 text-right">
          <button
            type="button"
            onClick={onViewResults}
            className="rounded-full border border-cyan-300/25 bg-cyan-300/[0.08] px-4 py-2 font-mono text-xs font-semibold text-cyan-100 transition hover:border-cyan-200/45 hover:bg-cyan-300/[0.14]"
          >
            View Full Results →
          </button>
        </div>
      )}
    </div>
  )
}
