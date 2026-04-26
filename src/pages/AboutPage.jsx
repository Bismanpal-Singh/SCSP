import React from 'react'
import { motion } from 'framer-motion'

const capabilities = [
  {
    title: 'Autonomous exploration',
    body: 'Explores large and complex material search spaces from a high-level research objective.',
  },
  {
    title: 'Iterative optimization',
    body: 'Uses each result to inform the next step, refining directions as evidence accumulates.',
  },
  {
    title: 'Reduced manual workflows',
    body: 'Minimizes repetitive research tasks across hypothesis, evaluation, and refinement loops.',
  },
  {
    title: 'Faster early-stage discovery',
    body: 'Helps identify promising candidates and research directions more quickly.',
  },
]

const fadeUp = {
  hidden: { opacity: 0, y: 18 },
  visible: { opacity: 1, y: 0 },
}

export default function AboutPage() {
  return (
    <main className="relative z-10 mx-auto min-h-screen w-full max-w-5xl px-4 py-14 sm:px-6 sm:py-18 lg:px-8">
      <div
        className="pointer-events-none absolute left-1/2 top-28 h-80 w-80 -translate-x-1/2 rounded-full bg-violet-500/10 blur-[90px]"
        aria-hidden
      />

      <motion.header
        initial="hidden"
        animate="visible"
        variants={fadeUp}
        transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1] }}
        className="relative text-center"
      >
        <h1 className="bg-gradient-to-b from-white via-violet-100 to-violet-400/90 bg-clip-text text-4xl font-bold tracking-tight text-transparent sm:text-5xl">
          About Mantle AI
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-base text-white/60 sm:text-lg">
          Autonomous intelligence for mineral and materials discovery
        </p>
      </motion.header>

      <motion.article
        initial="hidden"
        animate="visible"
        variants={fadeUp}
        transition={{ duration: 0.65, delay: 0.14, ease: [0.22, 1, 0.36, 1] }}
        className="relative mx-auto mt-12 max-w-4xl rounded-2xl border border-violet-500/18 bg-white/[0.045] px-5 py-8 text-left shadow-[0_0_60px_rgba(139,92,246,0.12),inset_0_1px_0_rgba(255,255,255,0.06)] backdrop-blur-xl sm:px-8 sm:py-10"
      >
        <Section title="Intro">
          <p>
            Mantle AI is an autonomous agent designed to accelerate mineral and materials discovery
            by reducing the manual effort required across the scientific workflow. Traditional
            research in materials science involves an iterative loop, forming hypotheses, testing
            candidates, analyzing results, and refining approaches. This process is often
            time-consuming, fragmented across tools, and heavily dependent on manual intervention.
          </p>
          <p>
            Mantle AI reimagines this loop as a continuous, intelligent system. Given a research
            objective, the system explores candidate material spaces, evaluates potential
            compositions, and iteratively improves results based on feedback.
          </p>
          <p>
            Instead of treating discovery as a sequence of disconnected steps, Mantle AI integrates
            exploration, evaluation, and refinement into a single streamlined pipeline. The goal is
            not just to analyze data, but to actively participate in the discovery process.
          </p>
        </Section>

        <Section title="How It Works">
          <p>
            Mantle AI is designed to work alongside modern materials datasets and simulation tools,
            allowing it to reason over structured scientific data and generate meaningful outputs
            from high-level research goals.
          </p>
        </Section>

        <Section title="Key Capabilities">
          <ul className="mt-5 grid gap-4">
            {capabilities.map((item) => (
              <li key={item.title} className="flex gap-3">
                <span className="mt-2 h-2 w-2 flex-shrink-0 rounded-full bg-violet-400 shadow-[0_0_14px_rgba(139,92,246,0.8)]" />
                <p className="text-sm leading-7 text-white/62 sm:text-base">
                  <span className="font-semibold text-white/88">{item.title}</span>
                  <span className="text-white/38"> — </span>
                  {item.body}
                </p>
              </li>
            ))}
          </ul>
        </Section>

        <Section title="Vision" isLast>
          <p>
            This approach is particularly valuable in domains where the search space is vast and the
            cost of experimentation is high. By narrowing down candidates and guiding exploration,
            Mantle AI helps researchers focus on the most promising directions rather than
            exhaustively testing possibilities.
          </p>
          <p>
            More broadly, Mantle AI represents a step toward autonomous laboratories, environments
            where AI systems assist not only in analyzing results but in driving experimentation
            itself. As these systems evolve, they have the potential to transform how scientific
            research is conducted: making it faster, more scalable, and more adaptive.
          </p>
          <p>
            Mantle AI is an early exploration of that vision, where discovery becomes a continuous,
            intelligent process rather than a manual, iterative one.
          </p>
        </Section>
      </motion.article>
    </main>
  )
}

function Section({ title, children, isLast = false }) {
  return (
    <section className={isLast ? '' : 'mb-8 border-b border-white/[0.07] pb-8'}>
      <h2 className="mb-4 font-mono text-[11px] uppercase tracking-[0.24em] text-violet-300/85">
        {title}
      </h2>
      <div className="space-y-5 text-sm leading-7 text-white/64 sm:text-base sm:leading-8">
        {children}
      </div>
    </section>
  )
}
