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

function firstSentence(text = '') {
  return humanize(
    String(text)
    .split(/(?<=[.!?])\s+/)
      .find(Boolean) || '',
  )
}

function outcomeDetail(iter) {
  const detail = firstSentence(iter.interpretation)
  if (detail) return detail
  return describeScore(iter.score)
}

function openingLine(iter, isFirst, previousIteration) {
  if (isFirst) {
    return "Searching for permanent magnets that do not require rare earth elements."
  }

  const pivot = previousIteration?.nextHypothesis || iter.nextHypothesis
  if (pivot) {
    return `${humanize(pivot)}.`
  }

  return `Trying a new direction around ${iter.bestFormula || 'the best option so far'}.`
}

export function narrateIteration(iter, isFirst, previousIteration = null) {
  return [
    openingLine(iter, isFirst, previousIteration),
    `Best option so far is ${iter.bestFormula} at score ${iter.score}. ${outcomeDetail(iter)}.`,
  ]
}

export function narrateFinal(finalCandidate = {}) {
  const formula = finalCandidate.formula || 'The final option'
  return [`Found it: ${formula} at score ${finalCandidate.score ?? 'n/a'}. Putting the report together now.`]
}

export function narrationTone(text = '') {
  const value = text.toLowerCase()
  if (value.includes('pivot') || value.includes('switching') || value.includes('strategy')) return 'pivot'
  if (value.includes('skipping') || value.includes('not good') || value.includes('breaks down') || value.includes('risk')) return 'reject'
  if (value.includes('holds up') || value.includes('above threshold') || value.includes('done') || value.includes('promising')) return 'success'
  return 'default'
}
