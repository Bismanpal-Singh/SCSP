import React from 'react'

export default function ResultsPanel({ finalCandidate }) {
  if (!finalCandidate) {
    return (
      <div className="rounded-xl border border-white/10 bg-black/20 p-5 text-left text-sm text-white/55">
        Final candidate will appear when the agent completes.
      </div>
    )
  }

  return (
    <div className="space-y-5 text-left">
      <div className="rounded-xl border border-violet-500/20 bg-black/25 p-5">
        <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-violet-300/80">
          Top candidate
        </p>
        <h3 className="mt-2 bg-gradient-to-r from-violet-200 to-indigo-200 bg-clip-text text-3xl font-bold tracking-tight text-transparent">
          {finalCandidate.formula}
        </h3>
        {finalCandidate.fullName && (
          <p className="mt-1 text-sm text-white/60">{finalCandidate.fullName}</p>
        )}
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <Metric label="Score" value={finalCandidate.score} />
        <Metric label="Magnetic moment" value={finalCandidate.magneticMoment} />
        <Metric label="Thermal stability" value={finalCandidate.thermalStability} />
        <Metric label="Formation energy" value={finalCandidate.formationEnergy} />
        <Metric label="Supply chain score" value={finalCandidate.supplyChainScore} />
        <Metric label="China dependency" value={finalCandidate.chinaDependency} />
      </div>

      {finalCandidate.synthesisRecommendation && (
        <div className="rounded-xl border border-violet-500/15 bg-violet-500/[0.06] p-4">
          <p className="font-mono text-[10px] uppercase tracking-wider text-violet-300/80">
            Synthesis recommendation
          </p>
          <p className="mt-2 text-sm leading-6 text-white/78">
            {finalCandidate.synthesisRecommendation}
          </p>
        </div>
      )}
    </div>
  )
}

function Metric({ label, value }) {
  if (value === undefined || value === null || value === '') return null

  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.03] p-3">
      <p className="text-xs text-white/40">{label}</p>
      <p className="mt-1 font-mono text-sm text-white/85">{value}</p>
    </div>
  )
}
