import React from 'react'

/**
 * Shared layout for subpages: consistent padding, title, and width under the same shell as the app.
 */
export default function SectionShell({ title, kicker, children }) {
  return (
    <main className="relative z-10 mx-auto min-h-[min(100vh,880px)] w-full max-w-4xl px-4 py-12 sm:px-6 sm:py-16 lg:px-8">
      <p className="text-center font-mono text-[10px] uppercase tracking-[0.25em] text-violet-400/80">
        {kicker}
      </p>
      <h1 className="mt-2 text-center text-3xl font-bold tracking-tight text-white sm:text-4xl">
        {title}
      </h1>
      <div className="mt-10">{children}</div>
    </main>
  )
}
