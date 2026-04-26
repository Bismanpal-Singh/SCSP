import React from 'react'

export default function LiveFeedPanel({ iterations = [], isRunning = false }) {
  if (iterations.length === 0) {
    return (
      <div className="rounded-xl border border-white/10 bg-black/20 p-5 text-left text-sm text-white/55">
        {isRunning ? 'Waiting for the first agent iteration...' : 'No iterations yet.'}
      </div>
    )
  }

  return (
    <div className="space-y-4 text-left">
      {iterations.map((iteration) => (
        <article
          key={iteration.num}
          className="rounded-xl border border-violet-500/20 bg-black/25 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.05)]"
        >
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-3">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-violet-300/80">
                Iteration {iteration.num}
              </p>
              <h3 className="mt-1 text-lg font-semibold text-white">{iteration.bestFormula || 'N/A'}</h3>
            </div>
            <div className="text-right font-mono text-xs text-white/60">
              <p>{iteration.candidatesTested} candidates</p>
              <p className="text-emerald-300/90">Score {iteration.score}</p>
            </div>
          </div>

          <div className="mt-3 space-y-2 rounded-lg border border-white/10 bg-white/[0.02] p-3 font-mono text-xs text-white/75">
            <p>1) Parsed hypothesis into structured spec.</p>
            <p>3) Scored candidates. Best eligible score this round: {iteration.score ?? 'N/A'}</p>
          </div>

          {iteration.bestCandidate && (
            <div className="mt-3 overflow-hidden rounded-lg border border-white/10 bg-black/20">
              <div className="grid grid-cols-3 gap-2 border-b border-white/10 px-3 py-2 font-mono text-[10px] uppercase tracking-[0.12em] text-white/45">
                <span>Formula</span>
                <span>Score</span>
                <span>Status</span>
              </div>
              <div className="grid grid-cols-3 gap-2 px-3 py-2 text-sm text-white/80">
                <span>{iteration.bestCandidate.formula || 'N/A'}</span>
                <span>{iteration.bestCandidate.score ?? 'N/A'}</span>
                <span>{iteration.bestCandidate.eligible === false ? 'INELIGIBLE' : 'ELIGIBLE'}</span>
              </div>
            </div>
          )}

          <p className="mt-3 text-sm leading-6 text-white/72">{iteration.interpretation}</p>
          {iteration.nextHypothesis && (
            <div className="mt-3 rounded-lg border border-violet-500/15 bg-violet-500/[0.06] p-3">
              <p className="font-mono text-[10px] uppercase tracking-wider text-violet-300/80">
                Next hypothesis
              </p>
              <p className="mt-1 text-sm text-white/78">{iteration.nextHypothesis}</p>
            </div>
          )}
          {iteration.status === 'converged' && (
            <p className="mt-3 font-mono text-xs text-emerald-300/90">
              Converged: best score exceeded threshold.
            </p>
          )}
        </article>
      ))}
    </div>
  )
}
