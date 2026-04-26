import React from 'react'

function statusBadgeTone(status = '') {
  if (status === 'TEST_FIRST') return 'border-emerald-400/30 bg-emerald-500/15 text-emerald-100'
  if (status === 'BACKUP_TEST') return 'border-amber-400/30 bg-amber-500/15 text-amber-100'
  if (status === 'SAFE_FALLBACK') return 'border-cyan-400/30 bg-cyan-500/15 text-cyan-100'
  if (status === 'EXPLORE_LATER') return 'border-white/20 bg-white/10 text-white/75'
  if (status === 'INELIGIBLE') return 'border-rose-400/30 bg-rose-500/15 text-rose-100'
  return 'border-white/20 bg-white/10 text-white/75'
}

export default function ResultsPanel({ finalCandidate, portfolio = [], ineligible = [], isRunning = false }) {
  if (!finalCandidate) {
    return (
      <div className="w-full rounded-xl border border-white/10 bg-black/20 p-5 text-left text-sm text-white/55">
        Final candidate will appear when the agent completes.
      </div>
    )
  }

  return (
    <div className="w-full space-y-5 text-left">
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

      {!isRunning && (
        <section className="rounded-xl border border-white/10 bg-black/20 p-4">
          <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-cyan-200/80">
            Ranked Material Portfolio
          </p>
          <div className="mt-3 overflow-x-auto">
            {portfolio.length === 0 ? (
              <p className="text-sm text-white/45">Portfolio loading...</p>
            ) : (
              <table className="w-full min-w-[760px] text-left text-xs">
                <thead className="text-white/45">
                  <tr className="border-b border-white/10">
                    <th className="py-2 pr-3">Rank</th>
                    <th className="py-2 pr-3">Candidate</th>
                    <th className="py-2 pr-3">Status</th>
                    <th className="py-2 pr-3">Overall</th>
                    <th className="py-2 pr-3">Sci Fit</th>
                    <th className="py-2 pr-3">Stability</th>
                    <th className="py-2 pr-3">Supply Risk</th>
                    <th className="py-2 pr-3">Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {portfolio.slice(0, 5).map((entry, index) => {
                    const scores = entry.scores || {}
                    const rowHighlight = index === 0 ? 'bg-emerald-400/[0.06] font-semibold' : ''
                    return (
                      <tr
                        key={`${entry.rank}-${entry.candidate}-${index}`}
                        className={`border-b border-white/5 text-white/80 ${rowHighlight}`}
                      >
                        <td className="py-2 pr-3 font-mono">{entry.rank ?? index + 1}</td>
                        <td className="py-2 pr-3">{entry.candidate || '—'}</td>
                        <td className="py-2 pr-3">
                          <span className={`rounded-md border px-2 py-1 text-[10px] font-semibold ${statusBadgeTone(entry.status)}`}>
                            {entry.status || '—'}
                          </span>
                        </td>
                        <td className="py-2 pr-3">{scores.overall ?? '—'}</td>
                        <td className="py-2 pr-3">{scores.scientific_fit ?? '—'}</td>
                        <td className="py-2 pr-3">{scores.stability ?? '—'}</td>
                        <td className="py-2 pr-3">{scores.supply_chain_safety ?? '—'}</td>
                        <td className="py-2 pr-3">{scores.evidence_confidence ?? '—'}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
          </div>
        </section>
      )}

      {!isRunning && (
        <section
          className={
            ineligible.length
              ? 'rounded-xl border border-rose-400/30 bg-rose-500/[0.06] p-4'
              : 'rounded-xl border border-white/10 bg-black/20 p-4'
          }
        >
          <p
            className={
              ineligible.length
                ? 'font-mono text-[10px] uppercase tracking-[0.18em] text-rose-100/85'
                : 'font-mono text-[10px] uppercase tracking-[0.18em] text-white/60'
            }
          >
            Rejected — Ineligible Candidates
          </p>
          {ineligible.length === 0 ? (
            <p className="mt-2 text-sm text-white/45">No candidates failed hard filters in this run.</p>
          ) : (
            <ul className="mt-3 space-y-2 text-sm">
              {ineligible.map((entry, idx) => (
                <li
                  key={`${entry.formula}-${idx}`}
                  className="flex gap-3 rounded-lg border border-rose-300/20 bg-black/20 p-3 text-rose-100/90"
                >
                  <span className="mt-0.5 text-rose-300">✗</span>
                  <div>
                    <p className="font-semibold">{entry.formula || 'Unknown'}</p>
                    <p className="mt-1 text-xs leading-5 text-rose-100/70">{entry.reason || 'Constraint violation'}</p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
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
