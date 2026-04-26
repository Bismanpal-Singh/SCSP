import React from 'react'
import SectionShell from './SectionShell'

const blocks = [
  {
    title: 'Autonomous Discovery Loop',
    body: 'Mantle AI translates mission intent into machine-readable constraints, ranks candidate materials with multi-objective scoring, and iterates hypotheses with traceable reasoning from each run.',
  },
  {
    title: 'Materials Intelligence Stack',
    body: 'The system combines crystal structure, thermodynamic stability, magnetic indicators, and supply-chain constraints so every recommendation is grounded in measurable evidence.',
  },
  {
    title: 'Decision-Ready Optimization',
    body: 'Portfolio outputs include ranked candidates, explicit rejection reasons, uncertainty mapping, and an ordered experiment queue that researchers can execute immediately.',
  },
]

export default function FeaturesPage() {
  return (
    <SectionShell title="Features" kicker="What Mantle can do">
      <div className="mx-auto grid max-w-3xl gap-6">
        {blocks.map((b) => (
          <article
            key={b.title}
            className="rounded-2xl border border-violet-500/15 bg-white/[0.04] p-6 shadow-[inset_0_1px_0_rgba(255,255,255,0.05)] backdrop-blur-md sm:p-8"
          >
            <h2 className="text-lg font-semibold text-violet-200 sm:text-xl">{b.title}</h2>
            <p className="mt-2 text-sm leading-relaxed text-white/60 sm:text-base">{b.body}</p>
          </article>
        ))}
      </div>
    </SectionShell>
  )
}
