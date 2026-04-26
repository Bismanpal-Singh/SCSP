import React from 'react'
import SectionShell from './SectionShell'

const blocks = [
  {
    title: 'Autonomous discovery loop',
    body: 'Mantle AI proposes hypotheses, runs virtual experiments, and refines candidates without manual iteration — closing the loop from goal to shortlist.',
  },
  {
    title: 'Materials data integration',
    body: 'Grounded in structured materials knowledge: compositions, properties, and stability signals inform every step of the search.',
  },
  {
    title: 'Optimization engine',
    body: 'Multi-objective scoring steers the agent toward practical compositions: stability, target properties, and process-aware constraints.',
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
