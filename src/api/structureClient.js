const MP_API_BASE = import.meta.env.DEV ? '/mp-api' : 'https://api.materialsproject.org'
const API_KEY = import.meta.env.VITE_MATERIALS_PROJECT_API_KEY || ''

const structureCache = new Map()
const formulaLookupCache = new Map()
const nameCache = new Map()

function requireApiKey() {
  if (!API_KEY) {
    throw new Error('Missing Materials Project API key. Set VITE_MATERIALS_PROJECT_API_KEY in your frontend environment.')
  }
}

function normalizeFormula(formula = '') {
  const subscriptDigits = {
    '₀': '0',
    '₁': '1',
    '₂': '2',
    '₃': '3',
    '₄': '4',
    '₅': '5',
    '₆': '6',
    '₇': '7',
    '₈': '8',
    '₉': '9',
  }
  const normalized = String(formula)
    .replace(/[₀-₉]/g, (digit) => subscriptDigits[digit] || digit)
    .replace(/\(.*?\)/g, ' ')
    .replace(/[^A-Za-z0-9]/g, ' ')
    .trim()

  const direct = normalized.replace(/\s+/g, '')
  if (/^[A-Z][A-Za-z0-9]*$/.test(direct)) {
    return direct
  }

  const match = normalized.match(/([A-Z][a-z]?\d*(?:[A-Z][a-z]?\d*)+)/)
  if (match?.[1]) return match[1]

  return normalized
    .replace(/\s+/g, '')
    .trim()
}

function headers() {
  return { 'X-API-KEY': API_KEY }
}

async function resolveMaterialName(formula = '') {
  const key = normalizeFormula(formula)
  if (!key) return null
  if (nameCache.has(key)) return nameCache.get(key)

  // Keep this deterministic and lightweight in the browser.
  const payload = {
    commonName: null,
    family: null,
    alternateNames: [],
    source: 'formula-fallback',
  }
  nameCache.set(key, payload)
  return payload
}

export async function fetchStructureByMpId(mpId) {
  if (!mpId) throw new Error('mpId is required')
  if (structureCache.has(mpId)) {
    return structureCache.get(mpId)
  }

  requireApiKey()

  try {
    const structRes = await fetch(
      `${MP_API_BASE}/materials/core/?material_ids=${encodeURIComponent(mpId)}&_fields=structure,formula_pretty,material_id`,
      { headers: headers() },
    )
    if (!structRes.ok) throw new Error(`MP API returned ${structRes.status}`)
    const structJson = await structRes.json()
    const structureEntry = structJson?.data?.[0]
    if (!structureEntry?.structure) throw new Error('No structure data returned')

    const sumRes = await fetch(
      `${MP_API_BASE}/materials/summary/?material_ids=${encodeURIComponent(mpId)}`
      + '&_fields=formula_pretty,chemsys,nelements,nsites,density,volume,'
      + 'symmetry,band_gap,formation_energy_per_atom,energy_above_hull,'
      + 'is_stable,is_magnetic,total_magnetization,ordering,theoretical,description',
      { headers: headers() },
    )
    if (!sumRes.ok) throw new Error(`MP summary returned ${sumRes.status}`)
    const sumJson = await sumRes.json()
    const summary = sumJson?.data?.[0] || {}

    const nameInfo = await resolveMaterialName(summary.formula_pretty || structureEntry.formula_pretty)

    const payload = {
      cif: null,
      structure: structureEntry.structure,
      formula: summary.formula_pretty || structureEntry.formula_pretty,
      commonName: nameInfo?.commonName || null,
      family: nameInfo?.family || null,
      alternateNames: nameInfo?.alternateNames || [],
      nameSource: nameInfo?.source || 'unknown',
      mpId,
      mpUrl: `https://next-gen.materialsproject.org/materials/${mpId}`,
      chemsys: summary.chemsys,
      nelements: summary.nelements,
      nsites: summary.nsites,
      density: summary.density,
      volume: summary.volume,
      symmetry: summary.symmetry,
      bandGap: summary.band_gap,
      formationEnergyPerAtom: summary.formation_energy_per_atom,
      energyAboveHull: summary.energy_above_hull,
      isStable: summary.is_stable,
      isMagnetic: summary.is_magnetic,
      totalMagnetization: summary.total_magnetization,
      magneticOrdering: summary.ordering,
      theoretical: summary.theoretical,
      description: summary.description,
    }

    structureCache.set(mpId, payload)
    if (payload.formula) formulaLookupCache.set(normalizeFormula(payload.formula), mpId)
    return payload
  } catch (err) {
    // eslint-disable-next-line no-console
    console.error('[structureClient] fetch failed:', err)
    throw err
  }
}

export async function fetchStructureByFormula(formula) {
  const normalizedFormula = normalizeFormula(formula)
  if (!normalizedFormula) throw new Error('formula is required')

  requireApiKey()

  if (formulaLookupCache.has(normalizedFormula)) {
    return fetchStructureByMpId(formulaLookupCache.get(normalizedFormula))
  }

  const summaryRes = await fetch(
    `${MP_API_BASE}/materials/summary/?formula=${encodeURIComponent(normalizedFormula)}&_fields=material_id,formula_pretty`,
    { headers: headers() },
  )
  if (!summaryRes.ok) throw new Error(`MP summary lookup returned ${summaryRes.status}`)
  const summaryJson = await summaryRes.json()
  const first = summaryJson?.data?.[0]
  const mpId = first?.material_id
  if (!mpId) {
    throw new Error(`No Materials Project entry found for formula ${normalizedFormula}`)
  }

  formulaLookupCache.set(normalizedFormula, mpId)
  return fetchStructureByMpId(mpId)
}

export function generateDescription(payload) {
  if (!payload) return ''
  if (payload.description) return payload.description

  const parts = []

  if (payload.commonName) {
    parts.push(`${payload.commonName} (${payload.formula})`)
  } else {
    parts.push(`${payload.formula}`)
  }

  if (payload.symmetry?.crystal_system) {
    parts.push(`crystallizes in the ${payload.symmetry.crystal_system.toLowerCase()} system`)
    if (payload.symmetry?.symbol) {
      parts.push(`(space group ${payload.symmetry.symbol})`)
    }
  }

  if (payload.nsites) {
    parts.push(`with ${payload.nsites} atoms per unit cell`)
  }

  const sentences = []
  sentences.push(`${parts.join(' ')}.`)

  if (payload.isStable !== undefined) {
    sentences.push(payload.isStable
      ? 'It is thermodynamically stable on the convex hull.'
      : 'It is metastable, lying above the convex hull.')
  }

  if (payload.isMagnetic) {
    const magnetizationValue = Number(payload.totalMagnetization)
    const magnetizationText = Number.isFinite(magnetizationValue)
      ? magnetizationValue.toFixed(2)
      : 'n/a'
    sentences.push(`Magnetic ordering: ${payload.magneticOrdering || 'magnetic'}, with total magnetization ${magnetizationText} μB per formula unit.`)
  }

  if (payload.bandGap !== undefined && payload.bandGap !== null) {
    const bandGapValue = Number(payload.bandGap)
    if (Number.isFinite(bandGapValue) && bandGapValue < 0.1) {
      sentences.push('It is metallic with no band gap.')
    } else if (Number.isFinite(bandGapValue)) {
      sentences.push(`It has a calculated band gap of ${bandGapValue.toFixed(2)} eV.`)
    }
  }

  if (payload.theoretical) {
    sentences.push('This entry is theoretical — calculated by DFT but not yet experimentally observed.')
  }

  return sentences.join(' ')
}
