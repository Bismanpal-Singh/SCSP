import React from 'react'
import MaterialLink from '../MaterialLink'

export default function DecisionLogPanel({ decisionLog = [] }) {
  if (decisionLog.length === 0) {
    return (
      <div className="rounded-xl border border-white/10 bg-black/20 p-5 text-left text-sm text-white/55">
        Decision log will appear when the agent completes.
      </div>
    )
  }

  return (
    <div className="space-y-3 text-left">
      {decisionLog.map((entry, index) => {
        const selected = entry.decision === 'selected'
        return (
          <article
            key={`${entry.iteration}-${entry.formula}-${index}`}
            className="rounded-xl border border-white/10 bg-black/25 p-4"
          >
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-white/38">
                  Iteration {entry.iteration}
                </p>
                <h3 className="mt-1 text-base font-semibold text-white">
                  <MaterialLink mpId={entry.mpId} formula={entry.formula}>
                    {entry.formula}
                  </MaterialLink>
                </h3>
              </div>
              <div className="flex items-center gap-3 font-mono text-xs">
                <span className={selected ? 'text-emerald-300/90' : 'text-rose-300/85'}>
                  {entry.decision}
                </span>
                <span className="text-white/45">Score {entry.score}</span>
              </div>
            </div>
            <p className="mt-3 text-sm leading-6 text-white/70">{entry.reason}</p>
          </article>
        )
      })}
    </div>
  )
}
