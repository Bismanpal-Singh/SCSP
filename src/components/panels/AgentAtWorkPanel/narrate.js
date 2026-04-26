export function describeScore(score) {
  const value = Number(score)
  if (!Number.isFinite(value)) return 'waiting for scored options'
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

function toolCallLine(iter = {}) {
  const action = String(iter.action || iter.status || '').trim().toLowerCase()
  if (!action) return ''
  if (action === 'retrieve_more') {
    return 'Action: `retrieve_more` -> calling retrieval/scoring tools for another pass.'
  }
  if (action === 'refine_direction') {
    return 'Action: `refine_direction` -> calling hypothesis generator for a new search direction.'
  }
  if (action === 'stop') {
    return 'Action: `stop` -> finalizing winner and synthesis recommendation.'
  }
  return `Action: \`${action}\` -> continuing workflow.`
}

function openingLine(iter, isFirst, previousIteration) {
  if (isFirst) {
    return "Searching for permanent magnets that don't need rare earth elements…"
  }

  const pivot = previousIteration?.nextHypothesis || iter.nextHypothesis
  if (pivot) {
    return `${humanize(pivot)}…`
  }

  return `Trying a new direction around ${iter.bestFormula || 'the best option so far'}…`
}

function bestOptionLine(iter = {}) {
  const formula = String(iter.bestFormula || iter.best_formula || iter.formula || '').trim()
  const score = Number(iter.score)
  const detail = outcomeDetail(iter)

  if (!formula && !Number.isFinite(score)) return ''
  if (!formula) return `Current score is ${score} — ${detail}.`
  if (!Number.isFinite(score)) return `Best option so far is ${formula} — ${detail}.`
  return `Best option so far is ${formula} at score ${score} — ${detail}.`
}

export function narrateIteration(iter, isFirst, previousIteration = null) {
  return [
    openingLine(iter, isFirst, previousIteration),
    toolCallLine(iter),
    bestOptionLine(iter),
  ].filter(Boolean)
}

export function narrateFinal(finalCandidate = {}) {
  const formula = finalCandidate.formula || 'The final option'
  return [`Found it: ${formula} at score ${finalCandidate.score ?? 'n/a'}. Putting the report together now…`]
}

export function narrationTone(text = '') {
  const value = text.toLowerCase()
  if (value.includes('pivot') || value.includes('switching') || value.includes('strategy')) return 'pivot'
  if (value.includes('skipping') || value.includes('not good') || value.includes('breaks down') || value.includes('risk')) return 'reject'
  if (value.includes('holds up') || value.includes('above threshold') || value.includes('done') || value.includes('promising')) return 'success'
  return 'default'
}
