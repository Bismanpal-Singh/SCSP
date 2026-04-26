import React, { useCallback, useEffect, useRef, useState } from 'react'
import { runAgent } from '../api/agentClient'
import { mockDecisionLog, mockDecisionTree, mockFinalCandidate, mockIterations, mockStructuredDecisionLog } from '../data/mockData'
import Button from './Button'
import TabNav from './TabNav'
import AgentAtWorkPanel from './panels/AgentAtWorkPanel'
import DecisionTreePanel from './panels/DecisionTreePanel'
import DecisionLogPanel from './panels/DecisionLogPanel'
import ResultsPanel from './panels/ResultsPanel'

function InputLeadingIcon() {
  return (
    <span className="pointer-events-none flex h-5 w-5 flex-shrink-0 text-violet-400/80" aria-hidden>
      <svg viewBox="0 0 24 24" fill="none" className="h-full w-full">
        <circle cx="12" cy="12" r="2.5" fill="currentColor" className="opacity-90" />
        <ellipse cx="12" cy="12" rx="9" ry="4" stroke="currentColor" strokeWidth="0.8" className="opacity-50" />
        <ellipse
          cx="12"
          cy="12"
          rx="9"
          ry="4"
          stroke="currentColor"
          strokeWidth="0.8"
          className="opacity-40"
          transform="rotate(60 12 12)"
        />
        <ellipse
          cx="12"
          cy="12"
          rx="9"
          ry="4"
          stroke="currentColor"
          strokeWidth="0.8"
          className="opacity-40"
          transform="rotate(120 12 12)"
        />
      </svg>
    </span>
  )
}

export default function InteractiveInput({ useMock = false }) {
  const [phase, setPhase] = useState('input')
  const [value, setValue] = useState('')
  const [submittedQuery, setSubmittedQuery] = useState('')
  const [iterations, setIterations] = useState([])
  const [finalCandidate, setFinalCandidate] = useState(null)
  const [decisionLog, setDecisionLog] = useState([])
  const [portfolio, setPortfolio] = useState([])
  const [ineligible, setIneligible] = useState([])
  const [testQueue, setTestQueue] = useState([])
  const [constraints, setConstraints] = useState({})
  const [provenanceTree, setProvenanceTree] = useState(null)
  const [terminalTranscript, setTerminalTranscript] = useState('')
  const [error, setError] = useState(null)
  const [isRunning, setIsRunning] = useState(false)
  const [activeTab, setActiveTab] = useState(0)
  const [shakeVersion, setShakeVersion] = useState(0)
  const inputRef = useRef(null)
  const runRef = useRef(null)
  const mockTimerIdsRef = useRef([])

  const expanded = phase === 'input'
  const isResults = phase === 'results'

  useEffect(() => {
    if (expanded && inputRef.current) {
      const id = requestAnimationFrame(() => inputRef.current?.focus())
      return () => cancelAnimationFrame(id)
    }
    return undefined
  }, [expanded])

  function openFromIdle() {
    if (phase !== 'idle') return
    setPhase('input')
  }

  function handleIdleKey(e) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      openFromIdle()
    }
  }

  const clearMockTimers = useCallback(() => {
    mockTimerIdsRef.current.forEach((id) => window.clearTimeout(id))
    mockTimerIdsRef.current = []
  }, [])

  const stopInFlightRun = useCallback(() => {
    runRef.current?.abort()
    runRef.current = null
    clearMockTimers()
  }, [clearMockTimers])

  useEffect(() => stopInFlightRun, [stopInFlightRun])

  const startMockRun = useCallback((query) => {
    mockIterations.forEach((iteration, index) => {
      const id = window.setTimeout(() => {
        setIterations((items) => [...items, iteration])
      }, (index + 1) * 1000)
      mockTimerIdsRef.current.push(id)
    })

    const completeId = window.setTimeout(() => {
      setFinalCandidate(mockFinalCandidate)
      setDecisionLog(mockDecisionLog)
      setPortfolio(mockStructuredDecisionLog.portfolio || [])
      setIneligible(mockStructuredDecisionLog.ineligible || [])
      setTestQueue(mockStructuredDecisionLog.testQueue || [])
      setConstraints(mockStructuredDecisionLog.constraints || {})
      setProvenanceTree(mockStructuredDecisionLog.provenanceTree || null)
      setTerminalTranscript('')
      setIsRunning(false)
      runRef.current = null
    }, (mockIterations.length + 1) * 1000)
    mockTimerIdsRef.current.push(completeId)
  }, [])

  const startRealRun = useCallback((query) => {
    runRef.current = runAgent(query, {
      onIteration: (iteration) => {
        setIterations((items) => [...items, iteration])
      },
      onComplete: (result) => {
        setFinalCandidate(result?.finalCandidate || null)
        setDecisionLog(Array.isArray(result?.decisionLog) ? result.decisionLog : [])
        setPortfolio(result?.portfolio || [])
        setIneligible(result?.ineligible || [])
        setTestQueue(result?.testQueue || [])
        setConstraints(result?.constraints || {})
        setProvenanceTree(result?.provenanceTree || null)
        setTerminalTranscript(result?.terminalTranscript || '')
        setIsRunning(false)
        runRef.current = null
      },
      onError: (err) => {
        setError(err?.message || 'Unable to run agent')
        setIsRunning(false)
        runRef.current = null
      },
    })
  }, [])

  const startRun = useCallback((query) => {
    stopInFlightRun()
    setSubmittedQuery(query)
    setIterations([])
    setFinalCandidate(null)
    setDecisionLog([])
    setPortfolio([])
    setIneligible([])
    setTestQueue([])
    setConstraints({})
    setProvenanceTree(null)
    setTerminalTranscript('')
    setError(null)
    setActiveTab(0)
    setIsRunning(true)
    setPhase('results')

    if (useMock) {
      startMockRun(query)
    } else {
      startRealRun(query)
    }
  }, [startMockRun, startRealRun, stopInFlightRun, useMock])

  function handleSubmit() {
    if (isRunning) return
    if (!expanded) return
    if (!value.trim()) {
      setShakeVersion((v) => v + 1)
      return
    }
    const query = value.trim()
    startRun(query)
  }

  function handleReset() {
    stopInFlightRun()
    setValue('')
    setSubmittedQuery('')
    setIterations([])
    setFinalCandidate(null)
    setDecisionLog([])
    setPortfolio([])
    setIneligible([])
    setTestQueue([])
    setConstraints({})
    setProvenanceTree(null)
    setTerminalTranscript('')
    setError(null)
    setIsRunning(false)
    setActiveTab(0)
    setPhase('input')
  }

  function handleRetry() {
    if (!submittedQuery) return
    startRun(submittedQuery)
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const [shaking, setShaking] = useState(false)
  useEffect(() => {
    if (shakeVersion === 0) return
    setShaking(true)
    const t = window.setTimeout(() => setShaking(false), 450)
    return () => clearTimeout(t)
  }, [shakeVersion])

  if (isResults) {
    return (
      <ResultsSurface
        activeTab={activeTab}
        decisionLog={decisionLog}
        error={error}
        finalCandidate={finalCandidate}
        portfolio={portfolio}
        ineligible={ineligible}
        testQueue={testQueue}
        constraints={constraints}
        provenanceTree={provenanceTree}
        isRunning={isRunning}
        iterations={iterations}
        mockDecisionTree={useMock ? mockDecisionTree : null}
        onReset={handleReset}
        onRetry={handleRetry}
        onTabChange={setActiveTab}
        query={submittedQuery}
        terminalTranscript={terminalTranscript}
      />
    )
  }

  return (
    <>
      <div
        className={[
          'mx-auto w-full max-w-2xl transition duration-300 ease-out',
          'opacity-100',
        ].join(' ')}
      >
        <>
          <div
            data-magnetic="true"
            className={[
              'overflow-hidden rounded-2xl border border-violet-500/30 bg-gradient-to-b from-white/[0.08] to-white/[0.02] shadow-[0_0_32px_rgba(139,92,246,0.18)] backdrop-blur-2xl transition-[min-height,box-shadow,border-color,transform] duration-500 ease-[cubic-bezier(0.33,0.9,0.2,1)]',
              expanded
                ? 'min-h-0 p-1 shadow-[0_0_0_1px_rgba(139,92,246,0.4),0_0_48px_rgba(139,92,246,0.2),inset_0_0_24px_rgba(139,92,246,0.08)]'
                : 'min-h-[3.5rem] cursor-pointer p-0 shadow-[0_0_28px_rgba(139,92,246,0.2)] sm:min-h-[3.75rem]',
              expanded && shaking ? 'animate-shake border-rose-500/30' : '',
            ]
              .filter(Boolean)
              .join(' ')}
          >
            {phase === 'idle' ? (
              <div
                data-magnetic="true"
                role="button"
                tabIndex={0}
                onClick={openFromIdle}
                onKeyDown={handleIdleKey}
                className="flex min-h-[3.5rem] w-full items-center justify-center px-5 py-4 text-sm font-medium text-white/85 transition duration-300 ease-out hover:bg-white/[0.04] hover:text-white sm:min-h-[3.75rem] sm:py-5 sm:text-base"
              >
                Enter your research goal
              </div>
            ) : (
              <div className="flex min-h-[52px] items-center gap-3 rounded-[12px] px-3 py-2.5 sm:px-4">
                <InputLeadingIcon />
                <input
                  ref={inputRef}
                  id="mantle-interactive-input"
                  type="text"
                  value={value}
                  onChange={(e) => setValue(e.target.value)}
                  onKeyDown={handleKeyDown}
                  autoComplete="off"
                  placeholder="What material are you trying to discover or optimize?"
                  className="min-w-0 flex-1 border-0 bg-transparent text-sm text-white/95 placeholder-white/32 outline-none ring-0 sm:text-base"
                />
              </div>
            )}
          </div>

          {expanded && (
            <div className="mt-4 flex justify-center">
              <Button
                onClick={handleSubmit}
                isLoading={false}
                isDimmed={!value.trim()}
                size="sm"
              >
                Run Agent
              </Button>
            </div>
          )}
        </>
      </div>
    </>
  )
}

function ResultsSurface({
  activeTab,
  constraints,
  decisionLog,
  error,
  finalCandidate,
  ineligible,
  isRunning,
  iterations,
  mockDecisionTree,
  onReset,
  onRetry,
  onTabChange,
  portfolio,
  provenanceTree,
  query,
  terminalTranscript,
  testQueue,
}) {
  return (
    <div className="w-full px-2 opacity-0 animate-fade-in sm:px-4 lg:px-6">
      <div className="overflow-hidden rounded-2xl border border-violet-500/20 bg-[#050509]/90 shadow-[0_0_44px_rgba(139,92,246,0.12),inset_0_1px_0_rgba(255,255,255,0.05)] backdrop-blur-xl">
        <div className="border-b border-white/[0.07] bg-white/[0.035] px-4 py-3">
          <div className="text-left">
            <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-violet-300/70">
              Mantle AI Agent
            </p>
            <p className="mt-1 w-full break-words text-sm text-white/65">&ldquo;{query}&rdquo;</p>
          </div>
        </div>

        <div className="px-4 py-4 sm:px-6 sm:py-5">
          <div className="mb-4 flex items-center justify-between gap-3 text-left">
            <span className="font-mono text-xs text-white/45">
              {isRunning ? 'Running...' : finalCandidate ? 'Complete' : 'Stopped'}
            </span>
            <div className="flex items-center gap-3">
              {isRunning && <span className="pulse-dot" aria-label="Agent running" />}
              <Button onClick={onReset} size="sm">
                New Search
              </Button>
            </div>
          </div>

          {error && (
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-rose-500/25 bg-rose-500/[0.08] p-3 text-left">
              <p className="text-sm text-rose-100/85">{error}</p>
              <button
                type="button"
                onClick={onRetry}
                className="rounded-md border border-rose-300/25 px-3 py-1.5 text-xs font-semibold text-rose-100/85 transition hover:bg-rose-300/10"
              >
                Retry
              </button>
            </div>
          )}

          <TabNav activeTab={activeTab} onTabChange={onTabChange} />
          <div className="pt-4">
            {activeTab === 0 && (
              <AgentAtWorkPanel
                finalCandidate={finalCandidate}
                isRunning={isRunning}
                iterations={iterations}
                onViewReasoning={() => onTabChange(2)}
                onViewResults={() => onTabChange(1)}
              />
            )}
            {activeTab === 1 && (
              <div className="space-y-5">
                <ResultsPanel
                  finalCandidate={finalCandidate}
                  ineligible={ineligible}
                  isRunning={isRunning}
                  portfolio={portfolio}
                />
                <section className="rounded-xl border border-white/10 bg-black/20 p-4 text-left">
                  <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-white/60">Decision Log</p>
                  <div className="mt-3">
                    <DecisionLogPanel decisionLog={decisionLog} />
                  </div>
                </section>
              </div>
            )}
            {activeTab === 2 && (
              <DecisionTreePanel
                constraints={constraints}
                decisionLog={decisionLog}
                decisionTree={mockDecisionTree}
                finalCandidate={finalCandidate}
                ineligible={ineligible}
                isRunning={isRunning}
                iterations={iterations}
                portfolio={portfolio}
                provenanceTree={provenanceTree}
                query={query}
                terminalTranscript={terminalTranscript}
                testQueue={testQueue}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
