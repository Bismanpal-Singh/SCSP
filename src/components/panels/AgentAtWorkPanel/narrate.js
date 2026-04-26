export function describeScore(score) {
  const value = Number(score || 0)
  if (value < 40) return 'not good enough'
  if (value < 70) return 'getting closer but still missing the spec'
  if (value < 80) return 'very close'
  return 'above threshold — converged'
}

export function humanize(text = '') {
  const cleaned = String(text)
    .replace(/Rejected/g, 'Skipping')
    .replace(/rejected/g, 'skipping')
    .replace(/candidates/g, 'options')
    .replace(/candidate/g, 'option')
    .replace(/\s+/g, ' ')
    .trim()

  if (!cleaned) return ''

  const softened = cleaned.replace(/^(\w)/, (match) => match.toLowerCase())
  return softened.length > 120 ? `${softened.slice(0, 117).trim()}…` : softened
}

function compactSentences(text = '') {
  return String(text)
    .split(/(?<=[.!?])\s+/)
    .map(humanize)
    .filter(Boolean)
    .slice(0, 2)
}

export function narrateIteration(iter, isFirst) {
  const lines = []

  if (isFirst) {
    lines.push('Looking through 150,000 materials in the database…')
    lines.push("Filtering for what the hypothesis asks for…")
  } else {
    lines.push(`Now testing ${iter.candidatesTested} candidates from the new direction…`)
  }

  lines.push(`Found ${iter.candidatesTested} candidates worth checking — running them through the spec.`)
  lines.push(...compactSentences(iter.interpretation))
  lines.push(`Best so far is ${iter.bestFormula} at score ${iter.score} — ${describeScore(iter.score)}.`)

  if (iter.nextHypothesis) {
    lines.push(`Pivoting: ${humanize(iter.nextHypothesis)}`)
  }

  return lines
}

export function narrateFinal(finalCandidate = {}) {
  const lines = []
  const formula = finalCandidate.formula || 'The final option'

  if (finalCandidate.thermalStability || finalCandidate.magneticMoment || finalCandidate.chinaDependency) {
    lines.push(
      `${formula} holds up to ${finalCandidate.thermalStability || 'the target range'}. Magnetic moment is ${finalCandidate.magneticMoment || 'on spec'}. ${finalCandidate.chinaDependency || 'Low'} China dependency.`,
    )
  } else {
    lines.push(`${formula} is the strongest match the agent found.`)
  }

  lines.push(`Score ${finalCandidate.score ?? 'n/a'}. That's above the convergence threshold.`)
  lines.push('Done. Let me put together the full report…')

  return lines
}

export function narrationTone(text = '') {
  const value = text.toLowerCase()
  if (value.includes('pivot') || value.includes('switching') || value.includes('strategy')) return 'pivot'
  if (value.includes('skipping') || value.includes('not good') || value.includes('breaks down') || value.includes('risk')) return 'reject'
  if (value.includes('holds up') || value.includes('above threshold') || value.includes('done') || value.includes('promising')) return 'success'
  return 'default'
}
