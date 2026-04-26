import React, { useMemo, useState } from 'react'

const ROOT_ID = 'root'
const NODE_WIDTH = 118
const NODE_HEIGHT = 70
const LEVEL_GAP = 150

function slug(value, fallback) {
  return String(value || fallback)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
}

function oneLine(text = '') {
  return String(text).split(/(?<=[.!?])\s+/)[0] || 'Agent evaluated this branch against the target constraints.'
}

function synthesizeCandidates(iteration) {
  const baseScore = Number(iteration.score || 0)
  const formulas = [
    iteration.bestFormulaPlain || iteration.bestFormula || `candidate-${iteration.num}-a`,
    `branch-${iteration.num}-b`,
    `branch-${iteration.num}-c`,
  ]
  const reasons = String(iteration.interpretation || 'Candidate did not satisfy the full spec.')
    .split(/(?<=[.!?])\s+/)
    .filter(Boolean)

  return formulas.map((formula, index) => ({
    id: slug(`${iteration.num}-${formula}`, `iter-${iteration.num}-${index}`),
    formula: index === 0 ? iteration.bestFormula || formula : formula,
    score: Math.max(0, baseScore - index * 12),
    status: index === 0 && iteration.status === 'converged' ? 'winner' : index === 0 ? 'explored' : 'rejected',
    isBest: index === 0,
    reason: index === 0 ? iteration.interpretation : reasons[index - 1] || 'Rejected after constraint screening.',
  }))
}

function normalizeLevels({ decisionLog, finalCandidate, iterations }) {
  if (decisionLog.length > 0) {
    const grouped = decisionLog.reduce((groups, entry, index) => {
      const iteration = Number(entry.iteration || 1)
      if (!groups.has(iteration)) groups.set(iteration, [])
      groups.get(iteration).push({ ...entry, index })
      return groups
    }, new Map())

    return Array.from(grouped.entries())
      .sort(([a], [b]) => a - b)
      .map(([iteration, entries], levelIndex) => {
        const selected = entries.find((entry) => entry.decision === 'selected')
        const best = selected || entries.reduce((top, entry) => (
          Number(entry.score || 0) > Number(top.score || 0) ? entry : top
        ), entries[0])

        return {
          iteration,
          candidatesTested: iterations[levelIndex]?.candidatesTested || entries.length,
          bestScore: best?.score,
          candidates: entries.slice(0, 10).map((entry) => {
            const isWinner = entry.decision === 'selected' || entry.formula === finalCandidate?.formula
            const isBest = entry.formula === best?.formula
            return {
              ...entry,
              id: slug(`${iteration}-${entry.formula}-${entry.index}`, `iter-${iteration}-${entry.index}`),
              status: isWinner ? 'winner' : isBest ? 'explored' : 'rejected',
              isBest,
              reason: entry.reason || 'Scored by the agent during this iteration.',
            }
          }),
        }
      })
  }

  return iterations.map((iteration) => ({
    iteration: Number(iteration.num || 1),
    candidatesTested: iteration.candidatesTested,
    bestScore: iteration.score,
    candidates: synthesizeCandidates(iteration),
  }))
}

function normalizeMockTree(decisionTree) {
  if (!decisionTree?.levels) return null
  return decisionTree.levels.map((level) => ({
    iteration: level.iteration,
    candidatesTested: level.candidatesTested,
    bestScore: level.bestScore,
    candidates: level.candidates.map((candidate) => ({
      ...candidate,
      isBest: Boolean(candidate.isBest || candidate.status === 'winner'),
    })),
  }))
}

function buildTree({ decisionLog, decisionTree, finalCandidate, iterations, query }) {
  const levels = normalizeMockTree(decisionTree) || normalizeLevels({ decisionLog, finalCandidate, iterations })
  const widestLevel = Math.max(3, ...levels.map((level) => level.candidates.length))
  const viewWidth = Math.max(900, widestLevel * 145)
  const viewHeight = 130 + Math.max(1, levels.length) * LEVEL_GAP + 120
  const rootX = viewWidth / 2

  const root = {
    id: ROOT_ID,
    label: decisionTree?.root?.label || 'Hypothesis',
    description: query || decisionTree?.root?.description || 'Submitted research objective',
    x: rootX,
    y: 54,
    status: 'root',
  }

  const nodes = [root]
  const edges = []
  const pathIds = [ROOT_ID]
  let previousBestId = ROOT_ID

  levels.forEach((level, levelIndex) => {
    const y = 145 + levelIndex * LEVEL_GAP
    const count = level.candidates.length
    const spacing = Math.min(150, (viewWidth - 180) / Math.max(1, count - 1))
    const startX = rootX - ((count - 1) * spacing) / 2

    const bestCandidate =
      level.candidates.find((candidate) => candidate.status === 'winner') ||
      level.candidates.find((candidate) => candidate.isBest) ||
      level.candidates.reduce((top, candidate) => (
        Number(candidate.score || 0) > Number(top.score || 0) ? candidate : top
      ), level.candidates[0])

    level.candidates.forEach((candidate, index) => {
      const node = {
        ...candidate,
        iteration: level.iteration,
        x: startX + index * spacing,
        y,
        why: oneLine(iterations[levelIndex]?.interpretation || candidate.reason),
      }
      nodes.push(node)
      edges.push({
        from: previousBestId,
        to: node.id,
        type: node.id === bestCandidate?.id || node.status === 'winner' ? 'path' : 'sibling',
      })
    })

    if (bestCandidate) {
      previousBestId = bestCandidate.id
      pathIds.push(bestCandidate.id)
    }
  })

  const stats = {
    tested: levels.reduce((total, level) => total + Number(level.candidatesTested || level.candidates.length), 0),
    rejected: nodes.filter((node) => node.status === 'rejected').length,
    selected: nodes.filter((node) => node.status === 'winner').length || (finalCandidate ? 1 : 0),
    iterations: levels.length,
    score: finalCandidate?.score || levels[levels.length - 1]?.bestScore || 0,
  }

  return { edges, nodes, pathIds, root, stats, viewHeight, viewWidth }
}

function nodeStyles(node, isDimmed, isActive) {
  if (node.status === 'root') {
    return {
      fill: '#071827',
      stroke: '#22d3ee',
      opacity: isDimmed ? 0.35 : 1,
      filter: 'url(#cyanGlow)',
    }
  }
  if (node.status === 'winner') {
    return {
      fill: '#062414',
      stroke: '#34d399',
      opacity: isDimmed ? 0.45 : 1,
      filter: 'url(#greenGlow)',
    }
  }
  if (node.isBest || node.status === 'explored') {
    return {
      fill: '#171206',
      stroke: isActive ? '#fde68a' : '#f59e0b',
      opacity: isDimmed ? 0.45 : 1,
      filter: 'url(#amberGlow)',
    }
  }
  return {
    fill: '#090f1a',
    stroke: '#fb7185',
    opacity: isDimmed ? 0.25 : 0.55,
    filter: 'none',
  }
}

function formatPropName(value) {
  return String(value)
    .replace(/([A-Z])/g, ' $1')
    .replace(/^./, (letter) => letter.toUpperCase())
}

function DetailPanel({ node, onClose }) {
  if (!node || node.status === 'root') return null

  const hiddenKeys = new Set(['x', 'y', 'id', 'index', 'isBest', 'why', 'reason', 'status', 'decision'])
  const properties = Object.entries(node).filter(([key, value]) => (
    !hiddenKeys.has(key) && value !== null && value !== undefined && value !== ''
  ))

  return (
    <aside className="absolute right-0 top-0 z-20 h-full w-full max-w-sm border-l border-cyan-300/15 bg-[#06111f]/95 p-5 text-left shadow-[-20px_0_45px_rgba(0,0,0,0.35)] backdrop-blur-xl animate-fade-in">
      <button
        type="button"
        onClick={onClose}
        className="float-right font-mono text-xs uppercase tracking-[0.16em] text-white/45 transition hover:text-white"
      >
        Close
      </button>
      <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-cyan-200/70">
        Node detail
      </p>
      <div className="mt-5 rounded-2xl border border-cyan-300/20 bg-cyan-300/[0.06] p-4">
        <p className="text-3xl font-bold text-white">{node.formula}</p>
        <p className="mt-2 font-mono text-sm text-cyan-100/75">Score {node.score ?? 'n/a'}</p>
      </div>

      <div className="mt-5 grid gap-2">
        {properties.map(([key, value]) => (
          <div key={key} className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2">
            <p className="text-[11px] text-white/38">{formatPropName(key)}</p>
            <p className="mt-1 font-mono text-xs text-white/78">{String(value)}</p>
          </div>
        ))}
      </div>

      <div className="mt-5 rounded-xl border border-white/10 bg-black/20 p-4">
        <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-white/42">
          Reason
        </p>
        <p className="mt-2 text-sm leading-6 text-white/75">{node.reason}</p>
      </div>

      <div className="mt-3 rounded-xl border border-amber-300/15 bg-amber-300/[0.05] p-4">
        <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-amber-200/60">
          Why this matters
        </p>
        <p className="mt-2 text-sm leading-6 text-white/72">{node.why}</p>
      </div>
    </aside>
  )
}

export default function DecisionTreePanel({
  decisionLog = [],
  decisionTree = null,
  finalCandidate = null,
  iterations = [],
  query = '',
}) {
  const [selectedNode, setSelectedNode] = useState(null)
  const [hovered, setHovered] = useState(null)
  const [tooltip, setTooltip] = useState(null)

  const tree = useMemo(
    () => buildTree({ decisionLog, decisionTree, finalCandidate, iterations, query }),
    [decisionLog, decisionTree, finalCandidate, iterations, query],
  )

  const hoveredChain = useMemo(() => {
    if (!hovered) return new Set()
    const parents = new Map(tree.edges.map((edge) => [edge.to, edge.from]))
    const chain = new Set([hovered])
    let cursor = hovered
    while (parents.has(cursor)) {
      cursor = parents.get(cursor)
      chain.add(cursor)
    }
    return chain
  }, [hovered, tree.edges])

  if (tree.nodes.length <= 1) {
    return (
      <div className="rounded-xl border border-white/10 bg-black/20 p-5 text-left text-sm text-white/55">
        Decision tree will grow as agent iterations arrive.
      </div>
    )
  }

  return (
    <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-[#050a13] text-left shadow-[0_0_44px_rgba(34,211,238,0.08)]">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 bg-white/[0.035] px-4 py-3">
        <p className="font-mono text-xs text-white/65">
          {tree.stats.tested} candidates tested  ·  {tree.stats.rejected} rejected  ·  {tree.stats.selected} selected  ·  {tree.stats.iterations} iterations  ·  converged at {tree.stats.score}
        </p>
        <span className="rounded-full border border-emerald-300/20 bg-emerald-300/[0.06] px-3 py-1 font-mono text-[10px] uppercase tracking-[0.16em] text-emerald-100/70">
          Decision Tree
        </span>
      </div>

      <div className="relative h-[560px] overflow-auto">
        <svg
          className="min-h-full min-w-full"
          viewBox={`0 0 ${tree.viewWidth} ${tree.viewHeight}`}
          role="img"
          aria-label="Agent decision tree"
        >
          <defs>
            <filter id="cyanGlow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="4" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
            <filter id="amberGlow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
            <filter id="greenGlow" x="-60%" y="-60%" width="220%" height="220%">
              <feGaussianBlur stdDeviation="5" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {tree.edges.map((edge, index) => {
            const from = tree.nodes.find((node) => node.id === edge.from)
            const to = tree.nodes.find((node) => node.id === edge.to)
            if (!from || !to) return null
            const active = hoveredChain.has(edge.from) && hoveredChain.has(edge.to)
            const path = `M ${from.x} ${from.y + 34} C ${from.x} ${(from.y + to.y) / 2}, ${to.x} ${(from.y + to.y) / 2}, ${to.x} ${to.y - 34}`
            const isMainPath = edge.type === 'path'
            return (
              <path
                key={`${edge.from}-${edge.to}`}
                d={path}
                fill="none"
                stroke={active || isMainPath ? '#f59e0b' : '#94a3b8'}
                strokeDasharray={isMainPath ? '0' : '6 8'}
                strokeLinecap="round"
                strokeWidth={active ? 3.5 : isMainPath ? 2.5 : 1.2}
                opacity={active ? 1 : isMainPath ? 0.72 : 0.28}
                style={{
                  animation: `tree-draw 1.1s ease ${index * 80}ms both`,
                }}
              />
            )
          })}

          {tree.nodes.map((node, index) => {
            const isHovered = hovered === node.id
            const isDimmed = Boolean(hovered) && !hoveredChain.has(node.id) && !isHovered
            const styles = nodeStyles(node, isDimmed, isHovered)
            const isCircle = node.status === 'root'
            const title = node.status === 'root' ? node.label : node.formula
            const tag = node.status === 'winner' ? '✓ WINNER' : node.isBest ? '★ best' : node.status

            return (
              <g
                key={node.id}
                className="cursor-pointer"
                style={{
                  transformOrigin: `${node.x}px ${node.y}px`,
                  animation: `node-pop 480ms ease ${index * 90}ms both`,
                }}
                onClick={() => setSelectedNode(node)}
                onMouseEnter={(event) => {
                  setHovered(node.id)
                  setTooltip({
                    x: event.clientX,
                    y: event.clientY,
                    node,
                  })
                }}
                onMouseMove={(event) => {
                  setTooltip((current) => current && { ...current, x: event.clientX, y: event.clientY })
                }}
                onMouseLeave={() => {
                  setHovered(null)
                  setTooltip(null)
                }}
              >
                {isCircle ? (
                  <>
                    <circle cx={node.x} cy={node.y} r="34" {...styles} strokeWidth="2.4" />
                    <text x={node.x} y={node.y - 2} textAnchor="middle" className="fill-cyan-100 text-[12px] font-bold">
                      {title}
                    </text>
                    <text x={node.x} y={node.y + 48} textAnchor="middle" className="fill-slate-400 text-[10px]">
                      {node.description.slice(0, 42)}
                    </text>
                  </>
                ) : (
                  <>
                    {node.status === 'winner' && (
                      <ellipse
                        cx={node.x}
                        cy={node.y}
                        rx={NODE_WIDTH / 2 + 12}
                        ry={NODE_HEIGHT / 2 + 10}
                        fill="none"
                        stroke="#fbbf24"
                        strokeWidth="2"
                        opacity="0.75"
                        className="animate-pulse"
                      />
                    )}
                    <rect
                      x={node.x - NODE_WIDTH / 2}
                      y={node.y - NODE_HEIGHT / 2}
                      width={NODE_WIDTH}
                      height={NODE_HEIGHT}
                      rx="16"
                      {...styles}
                      strokeWidth={node.status === 'winner' ? 2.8 : node.isBest ? 2.4 : 1.4}
                    />
                    <text x={node.x} y={node.y - 10} textAnchor="middle" className="fill-white text-[14px] font-bold">
                      {title}
                    </text>
                    <text x={node.x} y={node.y + 10} textAnchor="middle" className="fill-slate-300 text-[11px]">
                      Score {node.score ?? 'n/a'}
                    </text>
                    <text
                      x={node.x}
                      y={node.y + 28}
                      textAnchor="middle"
                      className={node.status === 'winner' ? 'fill-emerald-200 text-[9px]' : node.isBest ? 'fill-amber-200 text-[9px]' : 'fill-rose-200 text-[9px]'}
                    >
                      {tag}
                    </text>
                  </>
                )}
              </g>
            )
          })}
        </svg>

        {tooltip && (
          <div
            className="pointer-events-none fixed z-30 w-[240px] rounded-xl border border-cyan-300/30 bg-[#06111f]/95 p-3 text-left text-xs text-white shadow-[0_0_28px_rgba(34,211,238,0.18)]"
            style={{
              left: Math.min(tooltip.x + 16, window.innerWidth - 260),
              top: Math.min(tooltip.y + 16, window.innerHeight - 180),
            }}
          >
            <p className="font-semibold text-white">{tooltip.node.formula || tooltip.node.label}</p>
            <p className="mt-1 font-mono text-cyan-100/70">
              Score {tooltip.node.score ?? 'n/a'} · {tooltip.node.status}
            </p>
            <p className="mt-2 leading-5 text-white/65">{tooltip.node.reason || tooltip.node.description}</p>
          </div>
        )}

        <DetailPanel node={selectedNode} onClose={() => setSelectedNode(null)} />
      </div>

      <style>{`
        @keyframes tree-draw {
          from { stroke-dashoffset: 180; opacity: 0; }
          to { stroke-dashoffset: 0; }
        }
        @keyframes node-pop {
          from { opacity: 0; transform: scale(0.82) translateY(12px); }
          to { opacity: 1; transform: scale(1) translateY(0); }
        }
      `}</style>
    </div>
  )
}
