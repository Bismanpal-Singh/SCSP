import React from 'react'

/**
 * Post-submit surface — mock “agent” output with glass card + fade-in.
 * `onReset` returns to the interactive entry flow.
 */
export default function OutputPanel({ query, onReset }) {
  return (
    <div className="w-full rounded-2xl border border-violet-500/20 bg-white/[0.05] p-6 shadow-[0_0_40px_rgba(139,92,246,0.12),inset_0_1px_0_rgba(255,255,255,0.06)] backdrop-blur-2xl opacity-0 animate-fade-in sm:p-8">
      <p className="mb-1 font-mono text-[10px] uppercase tracking-[0.2em] text-violet-400/80">
        Result
      </p>
      {query && (
        <p className="mb-5 text-left text-sm text-white/50">
          <span className="text-white/40">Query:</span> <span className="text-white/80">&ldquo;{query}&rdquo;</span>
        </p>
      )}

      <h3 className="text-lg font-semibold text-white sm:text-xl">Top candidate</h3>
      <p className="mt-2 bg-gradient-to-r from-violet-200 to-indigo-200 bg-clip-text text-2xl font-bold tracking-tight text-transparent sm:text-3xl">
        LiFePO<span className="text-[0.65em] align-super">4</span> variant
      </p>

      <ul className="mt-5 space-y-2 border-t border-white/10 pt-5 text-left text-sm text-white/70">
        <li>
          <span className="text-white/40">Stability: </span>
          <span className="text-emerald-400/90">High</span>
        </li>
        <li>
          <span className="text-white/40">Band gap: </span>
          <span>2.8 eV</span>
        </li>
      </ul>

      <div className="mt-5 rounded-lg border border-violet-500/15 bg-violet-500/[0.06] p-4 text-left">
        <p className="font-mono text-[10px] uppercase tracking-wider text-violet-300/80">
          Suggested next step
        </p>
        <p className="mt-1.5 text-sm text-white/80">
          Explore Fe substitution range
        </p>
      </div>

      {onReset && (
        <button
          type="button"
          onClick={onReset}
          className="mt-6 w-full rounded-lg border border-white/15 py-2.5 text-sm font-medium text-white/60 transition hover:border-violet-500/40 hover:bg-white/[0.04] hover:text-violet-200"
        >
          New research
        </button>
      )}
    </div>
  )
}
