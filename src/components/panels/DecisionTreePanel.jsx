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
  decisionLog = [],
  decisionTree = null,
  finalCandidate = null,
  iterations = [],
  query = '',
}) {
  const [tooltipNode, setTooltipNode] = useState(null)
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 })
  const [tooltipLocked, setTooltipLocked] = useState(false)

  const tree = useMemo(
    () => normalizeTree({ decisionLog, decisionTree, finalCandidate, iterations, query }),
    [decisionLog, decisionTree, finalCandidate, iterations, query],
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

      <div className="w-full overflow-auto px-4 py-5">
        <svg
          viewBox={`0 0 ${VIEWBOX.width} ${VIEWBOX.height}`}
          className="mx-auto h-auto w-full min-w-[1100px]"
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
      <style>{`
        @keyframes winner-pulse {
          0%, 100% { filter: drop-shadow(0 0 16px rgba(0, 245, 212, 0.9)); }
          50% { filter: drop-shadow(0 0 28px rgba(0, 245, 212, 1)); }
        }
        .decision-tree-winner {
          animation: winner-pulse 2.4s ease-in-out infinite;
        }
      `}</style>
    </div>
  )
}
