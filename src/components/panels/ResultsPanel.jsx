import React from 'react'
import MaterialLink from '../MaterialLink'

const HEADER_HELP = {
  score: {
    definition: 'Final candidate overall score shown on the card.',
    formula: 'overall = 0.30*sci_fit + 0.20*stability + 0.20*supply_chain_safety + 0.15*manufacturability + 0.15*evidence_confidence',
  },
  formationEnergy: {
    definition: 'Formation energy per atom. Lower values are generally more stable.',
    formula: 'E_form = (E_total(material) - sum(n_i*mu_i)) / N_atoms',
  },
  rank: {
    definition: 'Position in the sorted portfolio list.',
    formula: 'Rank 1 is highest overall score after eligibility filters.',
  },
  candidate: {
    definition: 'Material formula for the portfolio entry.',
    formula: 'Candidate identifier from search/scoring output.',
  },
  status: {
    definition: 'Agent decision label for test priority.',
    formula: 'TEST_FIRST=top eligible, BACKUP_TEST=second, SAFE_FALLBACK=stable backup.',
  },
  overall: {
    definition: 'Final weighted score used for ordering.',
    formula: 'overall = 0.30*sci_fit + 0.20*stability + 0.20*supply_chain_safety + 0.15*manufacturability + 0.15*evidence_confidence',
  },
  sciFit: {
    definition: 'Domain-fit score for mission relevance.',
    formula: 'Class-aware; for permanent magnets this is primarily magnetic-performance fit.',
  },
  stability: {
    definition: 'Stability score for thermodynamic and structural robustness.',
    formula: 'Derived from stability indicators such as energy-above-hull.',
  },
  confidence: {
    definition: 'Evidence confidence score for data quality and completeness.',
    formula: 'Higher when MP metadata and computed properties are complete and coherent.',
  },
}

function statusBadgeTone(status = '') {
  if (status === 'TEST_FIRST') return 'border-emerald-400/30 bg-emerald-500/15 text-emerald-100'
  if (status === 'BACKUP_TEST') return 'border-amber-400/30 bg-amber-500/15 text-amber-100'
  if (status === 'SAFE_FALLBACK') return 'border-cyan-400/30 bg-cyan-500/15 text-cyan-100'
  if (status === 'EXPLORE_LATER') return 'border-white/20 bg-white/10 text-white/75'
  if (status === 'INELIGIBLE') return 'border-rose-400/30 bg-rose-500/15 text-rose-100'
  return 'border-white/20 bg-white/10 text-white/75'
}

function dedupeIneligible(items = []) {
  const merged = new Map()
  items.forEach((entry) => {
    const formula = String(entry?.formula || '').trim()
    if (!formula) return
    const key = formula.toUpperCase()
    const reason = String(entry?.reason || 'Constraint violation').trim()
    const existing = merged.get(key)
    if (!existing) {
      merged.set(key, { ...entry, formula, reasons: [reason] })
    } else if (!existing.reasons.includes(reason)) {
      existing.reasons.push(reason)
      merged.set(key, existing)
    }
  })
  return Array.from(merged.values()).map((entry) => ({
    ...entry,
    reason: entry.reasons.join(' ; '),
  }))
}

function materialSourceLabel(entry = {}) {
  const verificationSource = String(entry.verification_source || '')
  const existenceStatus = String(entry.existence_status || '')
  const source = String(entry.source || '').toLowerCase()
  const sourceType = String(entry.source_type || '')
  const sourceTypeLower = sourceType.toLowerCase()

  if (verificationSource === 'Materials Project' || existenceStatus === 'VERIFIED_IN_DATABASE') return 'Materials Project'
  if (sourceType === 'curated_evidence_fallback') return 'Curated'
  if (existenceStatus === 'FAMILY_OR_TEMPLATE') return 'Template'
  if (source.includes('llm') || sourceTypeLower.includes('llm')) return 'LLM'
  if (existenceStatus === 'NOT_FOUND_IN_DATABASE') return 'LLM / Unverified'
  return 'Unknown'
}

function SourcePill({ label, value }) {
  return (
    <span className="rounded-full border border-white/10 bg-white/[0.06] px-2 py-0.5 font-mono text-[10px] text-white/55">
      {label}: {value}
    </span>
  )
}

export default function ResultsPanel({ finalCandidate, portfolio = [], ineligible = [], isRunning = false }) {
  if (!finalCandidate) {
    return (
      <div className="w-full rounded-xl border border-white/10 bg-black/20 p-5 text-left text-sm text-white/55">
        Final candidate will appear when the agent completes.
      </div>
    )
  }

  const dedupedIneligible = dedupeIneligible(ineligible)
  const resolvedFormationEnergy = (
    finalCandidate?.formationEnergy
    ?? finalCandidate?.formation_energy
    ?? finalCandidate?.formationEnergyPerAtom
    ?? finalCandidate?.formation_energy_per_atom
  )

  return (
    <div className="w-full space-y-5 text-left">
      <div className="rounded-xl border border-violet-500/20 bg-black/25 p-5">
        <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-violet-300/80">
          Top candidate
        </p>
        <h3 className="mt-2 bg-gradient-to-r from-violet-200 to-indigo-200 bg-clip-text text-3xl font-bold tracking-tight text-transparent">
          <MaterialLink mpId={finalCandidate.mpId} formula={finalCandidate.formula}>
            {finalCandidate.formula}
          </MaterialLink>
        </h3>
        {finalCandidate.fullName && (
          <p className="mt-1 text-sm text-white/60">{finalCandidate.fullName}</p>
        )}
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <Metric label="Score" value={finalCandidate.score} help={HEADER_HELP.score} />
        <Metric label="Thermal stability" value={finalCandidate.thermalStability} />
        <Metric
          label="Formation energy"
          value={resolvedFormationEnergy ?? 'N/A'}
          help={HEADER_HELP.formationEnergy}
          forceShow
        />
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
                    <th className="py-2 pr-3"><HeaderHelpLabel label="Rank" help={HEADER_HELP.rank} /></th>
                    <th className="py-2 pr-3"><HeaderHelpLabel label="Candidate" help={HEADER_HELP.candidate} /></th>
                    <th className="py-2 pr-3"><HeaderHelpLabel label="Status" help={HEADER_HELP.status} /></th>
                    <th className="py-2 pr-3"><HeaderHelpLabel label="Overall" help={HEADER_HELP.overall} /></th>
                    <th className="py-2 pr-3"><HeaderHelpLabel label="Sci Fit" help={HEADER_HELP.sciFit} /></th>
                    <th className="py-2 pr-3"><HeaderHelpLabel label="Stability" help={HEADER_HELP.stability} /></th>
                    <th className="py-2 pr-3"><HeaderHelpLabel label="Confidence" help={HEADER_HELP.confidence} /></th>
                  </tr>
                </thead>
                <tbody>
                  {portfolio.slice(0, 5).map((entry, index) => {
                    const scores = entry.scores || {}
                    const rowHighlight = index === 0 ? 'bg-emerald-400/[0.06] font-semibold' : ''
                    const mpId = entry.mpId || entry.mp_id || entry.verification_id
                    return (
                      <tr
                        key={`${entry.rank}-${entry.candidate}-${index}`}
                        className={`border-b border-white/5 text-white/80 ${rowHighlight}`}
                      >
                        <td className="py-2 pr-3 font-mono">{entry.rank ?? index + 1}</td>
                        <td className="py-2 pr-3">
                          {entry.candidate ? (
                            <div className="space-y-1">
                              <MaterialLink mpId={mpId} formula={entry.candidate}>
                                {entry.candidate}
                              </MaterialLink>
                              <div className="flex flex-wrap gap-1.5">
                                <SourcePill label="Source" value={materialSourceLabel(entry)} />
                                {entry.verification_id && (
                                  <span className="rounded-full border border-cyan-300/15 bg-cyan-300/[0.06] px-2 py-0.5 font-mono text-[10px] text-cyan-100/60">
                                    MP: {entry.verification_id}
                                  </span>
                                )}
                              </div>
                            </div>
                          ) : '—'}
                        </td>
                        <td className="py-2 pr-3">
                          <span className={`rounded-md border px-2 py-1 text-[10px] font-semibold ${statusBadgeTone(entry.status)}`}>
                            {entry.status || '—'}
                          </span>
                        </td>
                        <td className="py-2 pr-3">{scores.overall ?? '—'}</td>
                        <td className="py-2 pr-3">{scores.scientific_fit ?? '—'}</td>
                        <td className="py-2 pr-3">{scores.stability ?? '—'}</td>
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
              dedupedIneligible.length
                ? 'font-mono text-[10px] uppercase tracking-[0.18em] text-rose-100/85'
                : 'font-mono text-[10px] uppercase tracking-[0.18em] text-white/60'
            }
          >
            Rejected — Ineligible Candidates
          </p>
          {dedupedIneligible.length === 0 ? (
            <p className="mt-2 text-sm text-white/45">No candidates failed hard filters in this run.</p>
          ) : (
            <ul className="mt-3 space-y-2 text-sm">
              {dedupedIneligible.map((entry, idx) => (
                <li
                  key={`${entry.formula}-${idx}`}
                  className="flex gap-3 rounded-lg border border-rose-300/20 bg-black/20 p-3 text-rose-100/90"
                >
                  <span className="mt-0.5 text-rose-300">✗</span>
                  <div>
                    <p className="font-semibold">
                      {entry.formula ? (
                        <MaterialLink mpId={entry.mpId} formula={entry.formula}>
                          {entry.formula}
                        </MaterialLink>
                      ) : 'Unknown'}
                    </p>
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

function HeaderHelpLabel({ label, help }) {
  return (
    <div className="group relative inline-flex items-center gap-1.5">
      <span>{label}</span>
      <span className="inline-flex h-3.5 w-3.5 items-center justify-center rounded-full border border-white/25 text-[9px] text-white/65">
        ?
      </span>
      <HelpTooltip help={help} />
    </div>
  )
}

function HelpTooltip({ help }) {
  if (!help) return null
  return (
    <div className="pointer-events-none absolute left-0 top-full z-30 mt-2 hidden w-80 rounded-md border border-violet-300/30 bg-[#0c1020] p-2.5 text-[11px] normal-case text-white/85 shadow-[0_12px_28px_rgba(0,0,0,0.45)] group-hover:block group-focus-within:block">
      <p><span className="font-semibold text-violet-200">Definition:</span> {help.definition}</p>
      <p className="mt-1"><span className="font-semibold text-violet-200">Formula:</span> {help.formula}</p>
    </div>
  )
}

function Metric({ label, value, help = null, forceShow = false }) {
  if (!forceShow && (value === undefined || value === null || value === '')) return null

  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.03] p-3">
      <div className="group relative inline-flex items-center gap-1.5">
        <p className="text-xs text-white/40">{label}</p>
        {help && (
          <>
            <span className="inline-flex h-3.5 w-3.5 items-center justify-center rounded-full border border-white/25 text-[9px] text-white/65">
              ?
            </span>
            <HelpTooltip help={help} />
          </>
        )}
      </div>
      <p className="mt-1 font-mono text-sm text-white/85">{value}</p>
    </div>
  )
}
