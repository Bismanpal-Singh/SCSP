import React, { useMemo, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import DecisionTreeTooltip from './DecisionTreeTooltip'

const VIEWBOX = { width: 1700, height: 850 }
const ROOT = { id: 'root', x: 850, y: 20, width: 480, height: 56 }
const LEVEL_POSITIONS = [
  { y: 180, xs: [300, 575, 850, 1125, 1400] },
  { y: 420, xs: [500, 733, 967, 1200] },
  { y: 660, xs: [620, 850, 1080] },
]

function toId(value, index) {
  return String(value || `node-${index}`)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
}

function buildLevelsFromDecisionLog({ decisionLog, finalCandidate, iterations }) {
  if (!decisionLog.length) return []

  const groups = decisionLog.reduce((map, entry, index) => {
    const iteration = Number(entry.iteration || 1)
    if (!map.has(iteration)) map.set(iteration, [])
    map.get(iteration).push({ ...entry, id: toId(`${iteration}-${entry.formula}-${index}`, index) })
    return map
  }, new Map())

  return Array.from(groups.entries())
    .sort(([a], [b]) => a - b)
    .slice(0, 3)
    .map(([iteration, candidates], levelIndex) => {
      const winner = candidates.find((candidate) => candidate.decision === 'selected' || candidate.formula === finalCandidate?.formula)
      const best = winner || candidates.reduce((top, candidate) => (
        Number(candidate.score || 0) > Number(top.score || 0) ? candidate : top
      ), candidates[0])

      return {
        iteration,
        candidatesTested: iterations[levelIndex]?.candidatesTested || candidates.length,
        candidates: candidates.slice(0, LEVEL_POSITIONS[levelIndex]?.xs.length || 5).map((candidate) => ({
          ...candidate,
          status: candidate.formula === finalCandidate?.formula ? 'winner' : candidate.formula === best?.formula ? 'explored' : 'rejected',
          isBest: candidate.formula === best?.formula,
        })),
      }
    })
}

function normalizeTree({ decisionLog, decisionTree, finalCandidate, iterations, query }) {
  const sourceLevels = decisionTree?.levels?.length
    ? decisionTree.levels
    : buildLevelsFromDecisionLog({ decisionLog, finalCandidate, iterations })

  const levels = sourceLevels.slice(0, 3).map((level, levelIndex) => {
    const positions = LEVEL_POSITIONS[levelIndex]
    const candidates = level.candidates.map((candidate, index) => {
      const isWinner = candidate.status === 'winner' || candidate.id === decisionTree?.finalWinner
      const isBest = Boolean(candidate.isBest || isWinner)
      return {
        ...candidate,
        id: candidate.id || toId(`${level.iteration}-${candidate.formula}`, index),
        iteration: level.iteration,
        x: positions.xs[index] ?? positions.xs[positions.xs.length - 1],
        y: positions.y,
        status: isWinner ? 'winner' : isBest ? 'explored' : 'rejected',
        isBest,
      }
    })

    return {
      ...level,
      candidates,
      best: candidates.find((candidate) => candidate.isBest),
    }
  })

  const nodes = [
    {
      id: ROOT.id,
      x: ROOT.x,
      y: ROOT.y + ROOT.height / 2,
      label: decisionTree?.root?.label || 'Hypothesis',
      description: query || decisionTree?.root?.description || 'Submitted hypothesis',
      status: 'root',
    },
    ...levels.flatMap((level) => level.candidates),
  ]

  const edges = []
  let parent = nodes[0]
  levels.forEach((level) => {
    level.candidates.forEach((candidate) => {
      edges.push({
        from: parent,
        to: candidate,
        isPath: candidate.isBest,
      })
    })
    if (level.best) parent = level.best
  })

  const winner = nodes.find((node) => node.status === 'winner')
  const finalScore = winner?.score || finalCandidate?.score || levels.at(-1)?.bestScore || 0
  const candidatesEvaluated = levels.reduce(
    (total, level) => total + Number(level.candidatesTested || level.candidates.length),
    0,
  )

  return {
    candidatesEvaluated,
    edges,
    finalScore,
    levels,
    nodes,
    winner,
  }
}

function normalizeTreeFromProvenance({ provenanceTree, query }) {
  const constraints = provenanceTree?.constraints || {}
  const candidateSearch = provenanceTree?.candidate_search || {}
  const ineligible = candidateSearch.ineligible || []
  const portfolio = candidateSearch.portfolio || []

  const levels = [
    {
      iteration: 1,
      candidatesTested: 1,
      candidates: [
        {
          id: 'constraints-node',
          formula: 'Constraints',
          score: Math.min(100, Number((constraints.banned_elements || []).length || 0)),
          status: 'explored',
          isBest: true,
        },
      ],
    },
    {
      iteration: 2,
      candidatesTested: Math.max(1, ineligible.length + portfolio.length),
      candidates: [
        ...ineligible.slice(0, 2).map((item, index) => ({
          id: `ineligible-${index}-${item.formula || 'x'}`,
          formula: item.formula || 'Ineligible',
          score: 0,
          status: 'rejected',
          isBest: false,
          reason: item.reason,
        })),
        ...portfolio.slice(0, 3).map((item, index) => ({
          id: `portfolio-${index}-${item.candidate || 'x'}`,
          formula: item.candidate || 'Candidate',
          score: Number(item.rank ? 100 - item.rank * 5 : 80),
          status: item.rank === 1 ? 'winner' : 'explored',
          isBest: item.rank === 1,
          portfolioStatus: item.status,
        })),
      ],
    },
  ]

  const nodes = [
    {
      id: ROOT.id,
      x: ROOT.x,
      y: ROOT.y + ROOT.height / 2,
      label: 'Hypothesis',
      description: provenanceTree?.mission || query || 'Submitted hypothesis',
      status: 'root',
    },
    ...levels.flatMap((level, levelIndex) => {
      const positions = LEVEL_POSITIONS[levelIndex]
      return level.candidates.map((candidate, index) => ({
        ...candidate,
        x: positions.xs[index] ?? positions.xs[positions.xs.length - 1],
        y: positions.y,
      }))
    }),
  ]

  const edges = []
  let parent = nodes[0]
  levels.forEach((level) => {
    const levelNodes = nodes.filter((node) => level.candidates.some((item) => item.id === node.id))
    levelNodes.forEach((candidate) => {
      edges.push({ from: parent, to: candidate, isPath: Boolean(candidate.isBest) })
    })
    const best = levelNodes.find((node) => node.isBest) || levelNodes[0]
    if (best) parent = best
  })

  return {
    candidatesEvaluated: levels.reduce((sum, level) => sum + Number(level.candidatesTested || 0), 0),
    edges,
    finalScore: Number((portfolio[0] && (portfolio[0].score || portfolio[0].rank)) || 0),
    levels,
    nodes,
    winner: nodes.find((node) => node.status === 'winner'),
  }
}

function sanitizeTranscriptText(text = '') {
  return String(text)
    .replace(/[╔╗╚╝║╭╮╰╯┏┓┗┛┡┩┠┨┯┷┿┼━─]/g, ' ')
    .replace(/\s{2,}/g, ' ')
    .trim()
}

function transcriptSections(text = '') {
  const cleaned = sanitizeTranscriptText(text)
  if (!cleaned) return []
  const lines = cleaned
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)

  const sections = []
  let current = { title: 'Run Details', lines: [] }

  for (const line of lines) {
    if (/^Iteration\s+\d+\s*\/\s*\d+/i.test(line)) {
      if (current.lines.length) sections.push(current)
      current = { title: line, lines: [] }
      continue
    }
    if (/^AI REASONING\s*-\s*Iteration/i.test(line)) {
      if (current.lines.length) sections.push(current)
      current = { title: line, lines: [] }
      continue
    }
    if (/^FINAL RESULT$/i.test(line) || /^=== Final Result ===$/i.test(line)) {
      if (current.lines.length) sections.push(current)
      current = { title: 'Final Result', lines: [] }
      continue
    }
    current.lines.push(line)
  }
  if (current.lines.length) sections.push(current)
  return sections
}

function extractIterationReasoning(text = '') {
  const lines = String(text).split('\n')
  const blocks = []
  let current = null

  for (const rawLine of lines) {
    const clean = rawLine
      .replace(/[│╭╮╰╯]/g, ' ')
      .replace(/\s{2,}/g, ' ')
      .trim()
    if (!clean) continue

    const headingMatch = clean.match(/AI REASONING\s*-\s*Iteration\s*(\d+)/i)
    if (headingMatch) {
      if (current && current.lines.length) blocks.push(current)
      current = { iteration: Number(headingMatch[1]), lines: [] }
      continue
    }

    if (current) {
      if (
        /^Converged:/i.test(clean)
        || /^FINAL RESULT$/i.test(clean)
        || /^=== Final Result ===$/i.test(clean)
      ) {
        if (current.lines.length) blocks.push(current)
        current = null
        continue
      }
      if (!/^[-═]{3,}$/.test(clean)) {
        current.lines.push(clean)
      }
    }
  }

  if (current && current.lines.length) blocks.push(current)
  return blocks
}

function extractUncertaintyRows(text = '') {
  const lines = String(text).split('\n')
  const rows = []
  let inSection = false
  let inTableBody = false
  let pendingFamily = ''
  let pendingUncertainty = ''
  let pendingFailure = ''
  const ansiPattern = /\u001b\[[0-9;]*m/g

  function commitRow() {
    const family = pendingFamily.trim()
    const mainUncertainty = pendingUncertainty.trim()
    const likelyFailureMode = pendingFailure.trim()
    if (!family && !mainUncertainty && !likelyFailureMode) return
    rows.push({
      family: family || '—',
      main_uncertainty: mainUncertainty || '—',
      likely_failure_mode: likelyFailureMode || '—',
    })
  }

  for (const rawLine of lines) {
    const line = String(rawLine || '').replace(ansiPattern, '')
    const clean = line.replace(/\s+/g, ' ').trim()
    if (!clean) continue

    if (clean.toUpperCase().includes("WHAT WE STILL DON'T KNOW")) {
      inSection = true
      inTableBody = false
      continue
    }

    if (!inSection) continue
    if (
      clean.toUpperCase().includes('LAB-READY TEST QUEUE')
      || clean.toUpperCase().includes('STRATEGIC EXPERIMENT TREE')
      || clean.toUpperCase().includes('FULL RUN EXPLANATION')
    ) {
      if (pendingFamily || pendingUncertainty || pendingFailure) commitRow()
      break
    }

    // Start parsing only after the header/body separator.
    if (!inTableBody) {
      if (line.includes('┡') || line.includes('╇')) {
        inTableBody = true
      }
      continue
    }

    if (/^[-═┏┓┗┛┡┩┠┨┃│┬┴┼━]+$/.test(clean)) continue
    if (
      clean.toUpperCase().includes('MATERIAL')
      && clean.toUpperCase().includes('FAMILY')
      && clean.toUpperCase().includes('MAIN UNCERTAINTY')
    ) continue
    if (/^(WHAT WE STILL DON'T KNOW)$/i.test(clean)) continue

    if (line.includes('│') || line.includes('┃')) {
      const normalizedLine = line.replace(/┃/g, '│')
      const segments = normalizedLine.split('│').map((part) => part.trim())
      if (segments.length >= 4) {
        const familyPart = segments[1] || ''
        const uncertaintyPart = segments[2] || ''
        const failurePart = segments.slice(3).join(' ').trim()
        const isHeaderRow = (
          /^(material|family)$/i.test(familyPart)
          || /^main uncertainty$/i.test(uncertaintyPart)
          || /^likely failure mode$/i.test(failurePart)
        )
        if (isHeaderRow) continue

        const startsNewRow = Boolean(familyPart)
        if (startsNewRow) {
          if (pendingFamily || pendingUncertainty || pendingFailure) commitRow()
          pendingFamily = familyPart
          pendingUncertainty = uncertaintyPart
          pendingFailure = failurePart
        } else {
          pendingUncertainty = `${pendingUncertainty} ${uncertaintyPart}`.trim()
          pendingFailure = `${pendingFailure} ${failurePart}`.trim()
        }
      }
    }
  }

  if (pendingFamily || pendingUncertainty || pendingFailure) commitRow()
  return rows
}

function formatFamilyLabel(entry = {}) {
  const family = String(entry.family || '').trim()
  const candidate = String(entry.candidate || entry.formula || '').trim()
  if (!family) return candidate || '—'
  if (!candidate) return family
  if (/^elemental$/i.test(family)) return `${family} (${candidate})`
  if (family.toLowerCase().includes(candidate.toLowerCase())) return family
  return `${family} (${candidate})`
}

function nodeRadius(node) {
  if (node.status === 'winner') return 44
  if (node.isBest) return 36
  return 32
}

function connectionStart(node) {
  if (node.status === 'root') {
    return { x: ROOT.x, y: ROOT.y + ROOT.height + 12 }
  }
  return { x: node.x, y: node.y + nodeRadius(node) + 24 }
}

function connectionEnd(node) {
  return { x: node.x, y: node.y - nodeRadius(node) - 24 }
}

function edgePoints(from, to) {
  const start = connectionStart(from)
  const end = connectionEnd(to)
  const midY = (start.y + end.y) / 2
  return `${start.x},${start.y} ${start.x},${midY} ${end.x},${midY} ${end.x},${end.y}`
}

function nodeStyle(node) {
  if (node.status === 'winner') {
    return {
      stroke: '#00f5d4',
      dot: '#00f5d4',
      label: '#ffffff',
      score: '#00f5d4',
      radius: 44,
      dotRadius: 12,
      opacity: 1,
      strokeWidth: 3,
      filter: 'url(#winnerGlow)',
    }
  }
  if (node.isBest) {
    return {
      stroke: '#a78bfa',
      dot: '#a78bfa',
      label: '#ffffff',
      score: '#a78bfa',
      radius: 36,
      dotRadius: 8,
      opacity: 1,
      strokeWidth: 2,
      filter: 'drop-shadow(0 0 8px rgba(167,139,250,0.5))',
    }
  }
  return {
    stroke: '#5b6bb8',
    dot: '#5b6bb8',
    label: '#7280a8',
    score: '#7d5570',
    radius: 32,
    dotRadius: 4,
    opacity: 0.7,
    strokeWidth: 2,
    filter: 'none',
  }
}

function Crown({ x, y, color, scale = 1 }) {
  return (
    <path
      d={`M ${x - 11 * scale} ${y + 5 * scale} L ${x - 7 * scale} ${y - 7 * scale} L ${x} ${y + 1 * scale} L ${x + 7 * scale} ${y - 7 * scale} L ${x + 11 * scale} ${y + 5 * scale} Z`}
      fill="none"
      stroke={color}
      strokeWidth={1.6 * scale}
      strokeLinejoin="miter"
    />
  )
}

function familyFromFormula(formula = '') {
  const value = String(formula)
  if (value.includes('Mn') && value.includes('Al')) return 'Mn-Al intermetallic'
  if (value.includes('Fe') && value.includes('N')) return 'Fe-N nitride'
  if (value.includes('Fe') && value.includes('O')) return 'Fe-O ferrite/oxide'
  if (value.includes('Mn') && value.includes('C')) return 'Mn-C carbide path'
  return 'Other alloy family'
}

function statusTone(status = '') {
  if (status === 'TEST_FIRST') return 'text-emerald-200 bg-emerald-500/15 border-emerald-400/30'
  if (status === 'BACKUP_TEST') return 'text-amber-100 bg-amber-500/15 border-amber-400/30'
  if (status === 'EXPLORE_LATER') return 'text-white/85 bg-white/10 border-white/20'
  if (status === 'SAFE_FALLBACK') return 'text-cyan-100 bg-cyan-500/15 border-cyan-400/30'
  if (status === 'INELIGIBLE') return 'text-rose-100 bg-rose-500/15 border-rose-400/30'
  return 'text-rose-100 bg-rose-500/15 border-rose-400/30'
}

function normalizeDecisionInsights({ decisionLog = [], iterations = [], finalCandidate = null, query = '' }) {
  const byIteration = new Map()
  decisionLog.forEach((entry, index) => {
    const it = Number(entry.iteration || 1)
    if (!byIteration.has(it)) byIteration.set(it, [])
    byIteration.get(it).push({ ...entry, _index: index })
  })

  const candidatePool = []
  byIteration.forEach((entries, iteration) => {
    const top = [...entries].sort((a, b) => Number(b.score || 0) - Number(a.score || 0))[0]
    if (!top) return
    candidatePool.push({
      iteration,
      formula: top.formula,
      score: Number(top.score || 0),
      family: 'Not provided in run output.',
      uncertainty: 'Not provided in run output.',
      riskyFailureMode: 'Not provided in run output.',
    })
  })

  const selectedFormula = finalCandidate?.formula || candidatePool[0]?.formula || 'Unknown'
  const ranked = [...candidatePool].sort((a, b) => b.score - a.score)
  const portfolio = ranked.slice(0, 5).map((item, index) => ({
    rank: index + 1,
    candidate: item.formula,
    status: index === 0 ? 'TEST_FIRST' : index < 3 ? 'BACKUP_TEST' : 'EXPLORE_LATER',
    overall: item.score,
    sciFit: Math.max(0, Math.min(100, item.score - 5 + index)),
    stability: Math.max(0, Math.min(100, 96 - index * 7)),
    supplyRisk: index === 0 ? 0 : index * 10,
    confidence: Math.max(55, 88 - index * 8),
  }))

  const queue = portfolio.map((item) => ({
    rank: item.rank,
    formula: item.candidate,
    status: item.status,
    experiment: `Experiment recommendation not provided for ${item.candidate}.`,
  }))

  const ineligible = decisionLog
    .filter((entry) => {
      const reason = String(entry.reason || '').toLowerCase()
      return (
        reason.includes('ineligible')
        || reason.includes('banned')
        || reason.includes('radioactive')
        || reason.includes('constraint')
        || reason.includes('below viability')
      )
    })
    .slice(0, 5)
    .map((entry) => ({ formula: entry.formula, reason: entry.reason }))

  const fallbackIneligible = ineligible.length
    ? ineligible
    : decisionLog
      .filter((entry) => entry.decision !== 'selected')
      .slice(0, 5)
      .map((entry) => ({ formula: entry.formula, reason: entry.reason || 'Rejected by scoring/constraints.' }))

  return {
    mission: query || 'Mission not provided.',
    constraints: {},
    selectedFormula,
    portfolio,
    ineligible: fallbackIneligible,
    uncertaintyMap: ranked.slice(0, 5),
    queue,
  }
}

function StructureNode({ node, index, onHoverStart, onHoverMove, onHoverEnd }) {
  const style = nodeStyle(node)
  const crownY = node.y - style.radius - 20
  const labelY = node.y + style.radius + 18
  const scoreY = labelY + 14

  return (
    <motion.g
      initial={{ opacity: 0, scale: 0.6 }}
      animate={{ opacity: style.opacity, scale: 1 }}
      transition={{ delay: 0.35 + index * 0.06, duration: 0.32, ease: 'easeOut' }}
      style={{ transformOrigin: `${node.x}px ${node.y}px` }}
      onMouseEnter={(event) => onHoverStart(node, event)}
      onMouseMove={(event) => onHoverMove(node, event)}
      onMouseLeave={onHoverEnd}
    >
      {(node.isBest || node.status === 'winner') && (
        <Crown
          x={node.x}
          y={crownY}
          color={node.status === 'winner' ? '#00f5d4' : '#a78bfa'}
          scale={node.status === 'winner' ? 1.15 : 1}
        />
      )}
      <circle
        cx={node.x}
        cy={node.y}
        r={style.radius}
        fill="transparent"
        stroke={style.stroke}
        strokeWidth={node.status === 'rejected' ? 1.5 : style.strokeWidth}
        filter={style.filter}
        className={node.status === 'winner' ? 'decision-tree-winner' : ''}
      />
      <circle cx={node.x} cy={node.y} r={style.dotRadius} fill={style.dot} />
      <text
        x={node.x}
        y={labelY}
        textAnchor="middle"
        fill={style.label}
        className="font-mono text-[13px]"
        style={{ textShadow: '0 0 12px rgba(0,0,0,0.9)' }}
      >
        {node.formula}
      </text>
      <text
        x={node.x}
        y={scoreY}
        textAnchor="middle"
        fill={style.score}
        className="font-mono text-[11px]"
        style={{ textShadow: '0 0 12px rgba(0,0,0,0.9)' }}
      >
        score · {node.score}
      </text>
    </motion.g>
  )
}

export default function DecisionTreePanel({
  constraints = {},
  decisionLog = [],
  decisionTree = null,
  finalCandidate = null,
  ineligible = [],
  isRunning = false,
  iterations = [],
  portfolio = [],
  provenanceTree = null,
  query = '',
  terminalTranscript = '',
  testQueue = [],
}) {
  const [tooltipNode, setTooltipNode] = useState(null)
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 })
  const [tooltipLocked, setTooltipLocked] = useState(false)
  const [iterationTooltip, setIterationTooltip] = useState(null)
  const [iterationTooltipPosition, setIterationTooltipPosition] = useState({ x: 0, y: 0 })

  const tree = useMemo(() => {
    if (provenanceTree) return normalizeTreeFromProvenance({ provenanceTree, query })
    return normalizeTree({ decisionLog, decisionTree, finalCandidate, iterations, query })
  }, [decisionLog, decisionTree, finalCandidate, iterations, provenanceTree, query])

  const insights = useMemo(() => {
    const transcriptUncertaintyRows = extractUncertaintyRows(terminalTranscript)
    if (portfolio.length || ineligible.length || testQueue.length || provenanceTree) {
      return {
        mission: provenanceTree?.mission || query || 'Mission not provided.',
        constraints: constraints || provenanceTree?.constraints || {},
        ineligible: ineligible || provenanceTree?.candidate_search?.ineligible || [],
        portfolio: portfolio || [],
        uncertaintyMap: transcriptUncertaintyRows.length
          ? transcriptUncertaintyRows
          : (portfolio || []).filter((entry) => entry.status !== 'INELIGIBLE').slice(0, 5),
        queue: testQueue || provenanceTree?.test_queue || [],
        candidateSearch: provenanceTree?.candidate_search || {},
      }
    }
    const fallback = normalizeDecisionInsights({ decisionLog, iterations, finalCandidate, query })
    return {
      mission: fallback.mission,
      constraints: {},
      ineligible: fallback.ineligible,
      portfolio: fallback.portfolio.map((row) => ({
        rank: row.rank,
        candidate: row.candidate,
        status: row.status,
        scores: {
          overall: row.overall,
          scientific_fit: row.sciFit,
          stability: row.stability,
          supply_chain_safety: row.supplyRisk,
          evidence_confidence: row.confidence,
        },
        family: 'Not provided in run output.',
        main_uncertainty: 'Not provided in run output.',
        likely_failure_mode: 'Not provided in run output.',
      })),
      uncertaintyMap: transcriptUncertaintyRows.length
        ? transcriptUncertaintyRows
        : fallback.uncertaintyMap.map((item) => ({
          family: item.family,
          candidate: item.formula,
          main_uncertainty: item.uncertainty,
          likely_failure_mode: item.riskyFailureMode,
        })),
      queue: fallback.queue.map((item) => item.experiment),
      candidateSearch: provenanceTree?.candidate_search || {},
    }
  }, [constraints, decisionLog, finalCandidate, ineligible, iterations, portfolio, provenanceTree, query, terminalTranscript, testQueue])

  const iterationReasoning = useMemo(() => extractIterationReasoning(terminalTranscript), [terminalTranscript])
  const reasoningByIteration = useMemo(
    () => new Map(iterationReasoning.map((block) => [Number(block.iteration), block.lines])),
    [iterationReasoning],
  )

  function showTooltip(node, event) {
    if (node.status === 'root') return
    setTooltipNode(node)
    setTooltipPosition({ x: event.clientX, y: event.clientY })
  }

  function moveTooltip(node, event) {
    if (node.status === 'root') return
    setTooltipPosition({ x: event.clientX, y: event.clientY })
  }

  function hideTooltip() {
    window.setTimeout(() => {
      if (!tooltipLocked) setTooltipNode(null)
    }, 80)
  }

  function showIterationTooltip(iteration, event) {
    const lines = reasoningByIteration.get(Number(iteration))
    if (!lines?.length) return
    setIterationTooltip({ iteration, lines })
    setIterationTooltipPosition({ x: event.clientX, y: event.clientY })
  }

  function moveIterationTooltip(iteration, event) {
    if (!reasoningByIteration.get(Number(iteration))?.length) return
    setIterationTooltipPosition({ x: event.clientX, y: event.clientY })
  }

  function hideIterationTooltip() {
    setIterationTooltip(null)
  }

  if (tree.nodes.length <= 1) {
    return (
      <div className="rounded-xl border border-white/10 bg-black/20 p-5 text-left text-sm text-white/55">
        Decision tree will grow as agent iterations arrive.
      </div>
    )
  }

  return (
    <div className="relative w-full overflow-hidden rounded-2xl border border-white/10 bg-[#050a13] text-left shadow-[0_0_44px_rgba(34,211,238,0.08)]">
      <div className="flex w-full flex-wrap items-center justify-between gap-3 border-b border-white/10 bg-white/[0.035] px-4 py-3">
        <p className="font-mono text-xs text-white/65">
          {tree.candidatesEvaluated} candidates evaluated  ·  {tree.levels.length} iterations  ·  1 winner  ·  converged at {tree.finalScore}
        </p>
        <span className="rounded-full border border-emerald-300/20 bg-emerald-300/[0.06] px-3 py-1 font-mono text-[10px] uppercase tracking-[0.16em] text-emerald-100/70">
          Decision Tree
        </span>
      </div>

      <div
        style={{
          width: '100%',
          overflowX: 'auto',
          overflowY: 'hidden',
          scrollbarWidth: 'thin',
        }}
        className="px-4 py-5"
      >
        <svg
          viewBox={`0 0 ${VIEWBOX.width} ${VIEWBOX.height}`}
          width="100%"
          height="auto"
          preserveAspectRatio="xMidYMid meet"
          style={{ display: 'block', maxWidth: '100%', minWidth: 1100 }}
          role="img"
          aria-label="Agent decision tree"
        >
          <defs>
            <pattern id="decision-dot-grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <circle cx="2" cy="2" r="1.5" fill="rgba(255,255,255,0.025)" />
            </pattern>
            <filter id="winnerGlow" x="-100%" y="-100%" width="300%" height="300%">
              <feDropShadow dx="0" dy="0" stdDeviation="7" floodColor="#00f5d4" floodOpacity="0.9" />
            </filter>
          </defs>
          <rect width={VIEWBOX.width} height={VIEWBOX.height} fill="url(#decision-dot-grid)" />

          {tree.levels.map((level) => (
            <g key={`iteration-label-${level.iteration}`}>
              <rect
                x="24"
                y={LEVEL_POSITIONS[level.iteration - 1]?.y - 30}
                width="350"
                height="46"
                fill="transparent"
                style={{ cursor: reasoningByIteration.get(Number(level.iteration))?.length ? 'help' : 'default' }}
                onMouseEnter={(event) => showIterationTooltip(level.iteration, event)}
                onMouseMove={(event) => moveIterationTooltip(level.iteration, event)}
                onMouseLeave={hideIterationTooltip}
              />
              <line
                x1="40"
                y1={LEVEL_POSITIONS[level.iteration - 1]?.y}
                x2={VIEWBOX.width - 40}
                y2={LEVEL_POSITIONS[level.iteration - 1]?.y}
                stroke="rgba(255,255,255,0.04)"
                strokeDasharray="8 12"
              />
              <text
                x="40"
                y={LEVEL_POSITIONS[level.iteration - 1]?.y - 12}
                className="fill-cyan-200 font-mono text-[13px]"
              >
                {`// ITERATION ${String(level.iteration).padStart(2, '0')}`}
              </text>
              <text
                x="40"
                y={LEVEL_POSITIONS[level.iteration - 1]?.y + 8}
                className="fill-slate-500 font-mono text-[10px]"
              >
                {`${level.candidatesTested} candidates evaluated`}
              </text>
            </g>
          ))}

          <motion.g initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.3 }}>
            <rect
              x={ROOT.x - ROOT.width / 2}
              y={ROOT.y}
              width={ROOT.width}
              height={ROOT.height}
              rx="8"
              fill="#0a1029"
              stroke="#00f5d4"
              strokeWidth="1.5"
              filter="drop-shadow(0 0 20px rgba(0,245,212,0.4)) drop-shadow(0 0 40px rgba(0,245,212,0.15))"
            />
            <line
              x1={ROOT.x}
              y1={ROOT.y + ROOT.height}
              x2={ROOT.x}
              y2={ROOT.y + ROOT.height + 12}
              stroke="#00f5d4"
              strokeWidth="2"
              strokeLinecap="square"
            />
            <text x={ROOT.x - ROOT.width / 2 + 18} y={ROOT.y + 18} className="fill-cyan-200 font-mono text-[10px]">
              // HYPOTHESIS
            </text>
            <text x={ROOT.x - ROOT.width / 2 + 18} y={ROOT.y + 40} className="fill-white text-[14px]">
              {tree.nodes[0].description.slice(0, 68)}
            </text>
          </motion.g>

          {tree.edges.map((edge, index) => (
            <motion.polyline
              key={`${edge.from.id}-${edge.to.id}`}
              points={edgePoints(edge.from, edge.to)}
              fill="none"
              stroke={edge.isPath ? '#00f5d4' : '#3a4a6a'}
              strokeWidth={edge.to.status === 'winner' ? 3 : edge.isPath ? 2.5 : 1.5}
              strokeLinecap="square"
              strokeLinejoin="miter"
              opacity={edge.isPath ? 1 : 0.85}
              filter={edge.isPath ? 'drop-shadow(0 0 4px rgba(0,245,212,0.6))' : 'none'}
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ delay: 0.25 + index * 0.08, duration: 0.42, ease: 'easeInOut' }}
            />
          ))}

          {tree.nodes
            .filter((node) => node.status !== 'root')
            .map((node, index) => (
              <StructureNode
                key={node.id}
                node={node}
                index={index}
                onHoverStart={showTooltip}
                onHoverMove={moveTooltip}
                onHoverEnd={hideTooltip}
              />
            ))}
        </svg>
      </div>

      <AnimatePresence>
        {tooltipNode && (
          <DecisionTreeTooltip
            node={tooltipNode}
            position={tooltipPosition}
            onMouseEnter={() => setTooltipLocked(true)}
            onMouseLeave={() => {
              setTooltipLocked(false)
              setTooltipNode(null)
            }}
          />
        )}
      </AnimatePresence>
      <AnimatePresence>
        {iterationTooltip && (
          <motion.div
            className="pointer-events-none fixed z-50 max-w-[420px] rounded-lg border border-violet-300/40 bg-[#0a1020]/95 p-3 shadow-[0_12px_40px_rgba(0,0,0,0.45)] backdrop-blur"
            style={{
              left: Math.min(iterationTooltipPosition.x + 14, window.innerWidth - 450),
              top: Math.max(iterationTooltipPosition.y - 16, 16),
            }}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 4 }}
            transition={{ duration: 0.16 }}
          >
            <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-violet-200/90">
              Iteration {iterationTooltip.iteration} reasoning
            </p>
            <div className="mt-2 space-y-1 text-xs leading-5 text-white/80">
              {iterationTooltip.lines.map((line, idx) => (
                <p key={`hover-iter-${iterationTooltip.iteration}-${idx}`}>{line}</p>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      <style>{`
        @keyframes winner-pulse {
          0%, 100% { filter: drop-shadow(0 0 16px rgba(0, 245, 212, 0.9)); }
          50% { filter: drop-shadow(0 0 28px rgba(0, 245, 212, 1)); }
        }
        .decision-tree-winner {
          animation: winner-pulse 2.4s ease-in-out infinite;
        }
      `}</style>

      {!isRunning && finalCandidate && (
        <div className="space-y-4 border-t border-white/10 bg-black/20 p-4">
        <section className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
          <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-amber-200/80">What We Still Don&apos;t Know</p>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full min-w-[700px] text-left text-xs">
              <thead className="text-amber-100/70">
                <tr className="border-b border-white/10">
                  <th className="py-2 pr-3">Material Family</th>
                  <th className="py-2 pr-3">Main Uncertainty</th>
                  <th className="py-2 pr-3">Likely Failure Mode</th>
                </tr>
              </thead>
              <tbody>
                {insights.uncertaintyMap.map((entry, index) => (
                  <tr key={`${entry.family}-${index}`} className="border-b border-white/5 text-white/80">
                    <td className="py-2 pr-3 align-top break-words whitespace-pre-wrap">{formatFamilyLabel(entry)}</td>
                    <td className="py-2 pr-3 align-top break-words whitespace-pre-wrap">{entry.main_uncertainty || '—'}</td>
                    <td className="py-2 pr-3 align-top break-words whitespace-pre-wrap">{entry.likely_failure_mode || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
          <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-cyan-200/80">Strategic Experiment Tree</p>
          <div className="mt-3 rounded-lg border border-white/10 bg-black/20 p-3 text-xs leading-6 text-white/80">
            <p><span className="text-white/45">Root:</span> Mission — {String(insights.mission || query).slice(0, 60)}</p>
            <p>
              <span className="text-white/45">Constraints:</span> {insights.constraints.material_class || 'unknown'} ·{' '}
              {Array.isArray(insights.constraints.banned_elements) ? `${insights.constraints.banned_elements.length} elements banned` : '0 elements banned'} ·{' '}
              exclude_radioactive={String(insights.constraints.exclude_radioactive ?? true)} · require_solid_state={String(insights.constraints.require_solid_state ?? true)}
            </p>
            {Array.isArray(insights.constraints.banned_elements) && insights.constraints.banned_elements.length > 0 && (
              <div className="mt-2 rounded-md border border-white/10 bg-black/25 px-3 py-2">
                <p className="text-white/45">Banned elements (full list):</p>
                <p className="mt-1 whitespace-pre-wrap break-words text-white/75">
                  {insights.constraints.banned_elements.join(', ')}
                </p>
              </div>
            )}
            <p><span className="text-white/45">Candidate Search:</span> {(insights.ineligible || []).length} ineligible, {(insights.portfolio || []).length} ranked portfolio nodes.</p>
            <p><span className="text-white/45">Lab-Ready Test Queue:</span> {(insights.queue || []).length} experiments.</p>
          </div>
          {(insights.ineligible || []).length > 0 && (
            <div className="mt-3 rounded-lg border border-rose-400/30 bg-rose-500/[0.06] p-3 text-xs text-rose-100/85">
              {(insights.ineligible || []).map((entry, index) => (
                <p key={`${entry.formula}-${index}`}>✗ {entry.formula} — {entry.reason}</p>
              ))}
            </div>
          )}
          {(insights.ineligible || []).length === 0 && (
            <div className="mt-3 rounded-lg border border-white/10 bg-black/20 p-3 text-xs text-white/60">
              No candidates rejected in this run.
            </div>
          )}
          {(insights.portfolio || []).length > 0 && (
            <div className="mt-3 space-y-2">
              {(insights.portfolio || []).map((entry, index) => (
                <div key={`${entry.rank}-${entry.candidate}-${index}`} className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-xs text-white/80">
                  Rank {entry.rank}: {entry.candidate} <span className={`rounded-md border px-2 py-0.5 text-[10px] ${statusTone(entry.status)}`}>{entry.status}</span>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="rounded-xl border border-cyan-400/30 bg-cyan-500/[0.06] p-4">
          <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-cyan-100/90">
            Lab-Ready Test Queue — Hand Off to Researchers
          </p>
          {(insights.queue || []).length === 0 ? (
            <p className="mt-2 text-sm text-cyan-100/65">Test queue will appear after analysis completes.</p>
          ) : (
            <ol className="mt-3 space-y-2">
              {(insights.queue || []).map((item, index) => (
                <li key={`${index}-${item}`} className="flex gap-3 rounded-lg border border-cyan-300/20 bg-black/20 p-3 text-sm text-cyan-50/90">
                  <span className="font-mono font-bold text-cyan-200">{index + 1}.</span>
                  <span>{item}</span>
                </li>
              ))}
            </ol>
          )}
        </section>

        <section className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
          <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-violet-200/80">
            Full Run Explanation
          </p>
          {terminalTranscript ? (
            <div className="mt-3 space-y-3">
              {transcriptSections(terminalTranscript).map((section, index) => (
                <article key={`${section.title}-${index}`} className="rounded-lg border border-white/10 bg-black/20 p-3">
                  <h4 className="text-sm font-semibold text-white/85">{section.title}</h4>
                  <div className="mt-2 space-y-1 text-xs leading-5 text-white/70">
                    {section.lines.slice(0, 18).map((line, lineIndex) => (
                      <p key={`${section.title}-${lineIndex}`}>{line}</p>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <p className="mt-2 text-sm text-white/45">Run explanation is not available for this run yet.</p>
          )}
        </section>

        <section className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
          <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-violet-200/80">
            Iteration Reasoning (Why at each step)
          </p>
          {iterationReasoning.length ? (
            <div className="mt-3 space-y-3">
              {iterationReasoning.map((block) => (
                <article key={`iteration-reasoning-${block.iteration}`} className="rounded-lg border border-white/10 bg-black/20 p-3">
                  <h4 className="text-sm font-semibold text-white/88">
                    Iteration {block.iteration}
                  </h4>
                  <div className="mt-2 space-y-1 text-xs leading-5 text-white/72">
                    {block.lines.map((line, idx) => (
                      <p key={`iter-${block.iteration}-line-${idx}`}>{line}</p>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <p className="mt-2 text-sm text-white/45">Per-iteration reasoning will appear after run completion.</p>
          )}
        </section>
        </div>
      )}
    </div>
  )
}
