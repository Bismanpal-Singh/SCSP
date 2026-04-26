import React from 'react'
import { motion } from 'framer-motion'

function statusLabel(node) {
  if (node.status === 'winner') return 'Winner'
  if (node.isBest) return 'Best so far'
  return 'Rejected'
}

function statusClass(node) {
  if (node.status === 'winner') return 'border-emerald-300/25 bg-emerald-300/[0.08] text-emerald-100'
  if (node.isBest) return 'border-amber-300/25 bg-amber-300/[0.08] text-amber-100'
  return 'border-rose-300/25 bg-rose-300/[0.08] text-rose-100'
}

function scoreColor(score) {
  if (score >= 80) return 'bg-emerald-300'
  if (score >= 60) return 'bg-amber-300'
  return 'bg-rose-300'
}

function Property({ label, value }) {
  if (!value) return null
  return (
    <div>
      <p className="text-[10px] uppercase tracking-[0.12em] text-white/35">{label}</p>
      <p className="mt-0.5 text-xs text-white/72">{value}</p>
    </div>
  )
}

export default function DecisionTreeTooltip({ node, position, onMouseEnter, onMouseLeave }) {
  if (!node) return null

  const flipLeft = position.x > window.innerWidth - 420
  const left = flipLeft ? position.x - 380 : position.x + 18
  const top = Math.min(position.y + 12, window.innerHeight - 330)
  const scoreWidth = `${Math.min(100, Math.max(0, (Number(node.score || 0) / 80) * 100))}%`

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 4 }}
      transition={{ duration: 0.2 }}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      className="fixed z-50 w-[360px] rounded-2xl border border-cyan-300/30 bg-[var(--surface)] p-4 text-left shadow-[0_18px_55px_rgba(0,0,0,0.45),0_0_24px_rgba(34,211,238,0.12)]"
      style={{ left, top }}
    >
      <div className="grid grid-cols-[1fr_90px] gap-4">
        <div className="min-w-0">
          <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-cyan-100/55">
            Iteration {node.iteration}
          </p>
          <h3 className="mt-1 text-2xl font-bold text-white">{node.formula}</h3>
          <p className="mt-1 text-xs text-white/48">{node.fullName || 'Material candidate'}</p>

          <div className="mt-3 flex items-center gap-2">
            <span className={`rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.12em] ${statusClass(node)}`}>
              {statusLabel(node)}
            </span>
            <span className="font-mono text-xs text-white/58">Score {node.score}</span>
          </div>

          <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/10">
            <div className={`h-full rounded-full ${scoreColor(node.score)}`} style={{ width: scoreWidth }} />
          </div>
          <p className="mt-1 text-[10px] text-white/35">Convergence threshold: 80</p>
        </div>

        <div className="flex h-[90px] w-[90px] items-center justify-center rounded-xl border border-cyan-300/15 bg-cyan-300/[0.04]">
          <div className="h-12 w-12 animate-spin rounded-full border border-cyan-200/20 border-t-cyan-200/70" />
        </div>
      </div>

      <div className="mt-4 rounded-xl border border-white/10 bg-black/20 p-3">
        <p className="text-xs leading-5 text-white/75">{node.reason}</p>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3">
        <Property label="Magnetic moment" value={node.magneticMoment} />
        <Property label="Thermal stability" value={node.thermalStability} />
        <Property label="Formation energy" value={node.formationEnergy} />
        <Property label="China dependency" value={node.chinaDependency} />
        <Property label="Supply risk" value={node.supplyChainRisk} />
        <Property label="MP ID" value={node.mpId} />
      </div>
    </motion.div>
  )
}
