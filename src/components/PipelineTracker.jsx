import React, { useEffect, useState } from 'react'
import PipelineStep from './PipelineStep'
import StatusText from './StatusText'
import MetricsPanel from './MetricsPanel'

const STEPS = [
  { title: 'Generate Candidates', subtitle: 'Searching chemical space', icon: 'spark' },
  { title: 'Query Materials Database', subtitle: 'Structured property lookups', icon: 'db' },
  { title: 'Evaluate Properties', subtitle: 'Stability & band analysis', icon: 'atom' },
  { title: 'Optimize Composition', subtitle: 'Multi-objective search', icon: 'tune' },
  { title: 'Rank & Select Output', subtitle: 'Scoring & final ranking', icon: 'rank' },
]

const STEP_MS = 1000
const TAIL_MS = 650

/**
 * Drives step timing (~1s per stage), then calls onComplete for handoff to results.
 */
export default function PipelineTracker({ onComplete }) {
  const [currentStep, setCurrentStep] = useState(0)

  useEffect(() => {
    const last = STEPS.length
    const ids = []
    for (let s = 1; s <= last; s += 1) {
      ids.push(window.setTimeout(() => setCurrentStep(s), STEP_MS * s))
    }
    ids.push(
      window.setTimeout(() => {
        onComplete()
      }, STEP_MS * last + TAIL_MS),
    )
    return () => ids.forEach(clearTimeout)
  }, [onComplete])

  function getStepState(i) {
    if (currentStep > i) return 'complete'
    if (i === currentStep) return 'active'
    return 'upcoming'
  }

  // Metrics track the “current” work — step index 0..4
  const m = Math.max(0, Math.min(currentStep, STEPS.length - 1))

  return (
    <div
      className="relative w-full max-w-5xl overflow-hidden rounded-2xl border border-violet-500/30 bg-gradient-to-b from-white/[0.1] to-white/[0.02] p-4 shadow-[0_0_0_1px_rgba(139,92,246,0.2),0_0_60px_rgba(139,92,246,0.15),inset_0_1px_0_rgba(255,255,255,0.08)] backdrop-blur-2xl sm:p-6"
      style={{ animation: 'morphIn 0.6s ease-out' }}
    >
      <div
        className="pointer-events-none absolute inset-0 transition-opacity duration-700"
        style={{
          opacity: 0.2 + (Math.min(currentStep, STEPS.length) / (STEPS.length * 1.2)) * 0.2,
          background: `radial-gradient(ellipse 80% 50% at ${
            STEPS.length < 2 ? 50 : (Math.min(currentStep, STEPS.length - 1) / (STEPS.length - 1)) * 100
          }% 0%, rgba(139, 92, 246, 0.22) 0%, transparent 55%)`,
        }}
        aria-hidden
      />

      <div className="mb-4 sm:mb-5">
        <p className="mb-0.5 text-center font-mono text-[9px] uppercase tracking-[0.2em] text-violet-400/80">
          AI reasoning pipeline
        </p>
        <StatusText />
      </div>

      <div className="mx-auto flex w-full max-w-4xl flex-col items-stretch justify-center gap-0 md:mx-0 md:flex-row md:items-stretch">
        {STEPS.map((step, i) => (
          <React.Fragment key={step.title}>
            {i > 0 && (
              <>
                <Connector isFilled={currentStep >= i} orientation="col" className="md:hidden" />
                <Connector isFilled={currentStep >= i} orientation="row" className="hidden md:flex" />
              </>
            )}
            <div className="w-full min-w-0 flex-1 md:max-w-[8.2rem]">
              <PipelineStep
                title={step.title}
                subtitle={step.subtitle}
                icon={step.icon}
                state={getStepState(i)}
              />
            </div>
          </React.Fragment>
        ))}
      </div>

      <div className="mt-5 flex w-full flex-col items-center justify-center gap-3 sm:mt-6 md:flex-row md:items-start md:gap-6">
        <p className="w-full text-center text-[10px] text-white/35 md:flex-1 md:text-left">
          Stages run in sequence. Connection lines fill as each step finishes.
        </p>
        <MetricsPanel activeStep={m} />
      </div>

      <style>{`
        @keyframes morphIn {
          from { opacity: 0.8; transform: scale(0.98) translateY(8px); }
          to { opacity: 1; transform: scale(1) translateY(0); }
        }
      `}</style>
    </div>
  )
}

function Connector({ isFilled, orientation, className = '' }) {
  if (orientation === 'row') {
    return (
      <div
        className={['relative h-[2px] min-w-2 flex-1 max-w-28 self-center', className]
          .filter(Boolean)
          .join(' ')}
        aria-hidden
      >
        <div className="absolute left-0 top-1/2 h-[2px] w-full -translate-y-1/2 rounded-full bg-white/10" />
        <div
          className="absolute left-0 top-1/2 h-[2px] max-w-full -translate-y-1/2 rounded-full bg-gradient-to-r from-violet-500 to-indigo-500 transition-all duration-700 ease-in-out"
          style={{ width: isFilled ? '100%' : '0%' }}
        />
      </div>
    )
  }
  return (
    <div
      className={['relative mx-auto h-4 w-3', className].filter(Boolean).join(' ')}
      aria-hidden
    >
      <div className="absolute inset-0 w-[2px] left-1/2 -translate-x-1/2 rounded-full bg-white/10" />
      <div
        className="absolute bottom-0 left-1/2 w-[2px] -translate-x-1/2 rounded-full bg-gradient-to-b from-violet-500 to-indigo-500 transition-all duration-700 ease-in-out"
        style={{ height: isFilled ? '100%' : '0%' }}
      />
    </div>
  )
}
