import React, { useState } from 'react'
import SectionShell from './SectionShell'

export default function ContactPage() {
  const [sent, setSent] = useState(false)

  function handleSubmit(e) {
    e.preventDefault()
    setSent(true)
  }

  return (
    <SectionShell title="Contact" kicker="Get in touch">
      <form
        onSubmit={handleSubmit}
        className="mx-auto w-full max-w-md space-y-4 rounded-2xl border border-violet-500/15 bg-white/[0.04] p-6 backdrop-blur-md sm:p-8"
      >
        <p className="text-center text-sm text-white/45">
          Placeholder form — connect your team email or API in production.
        </p>
        <label className="block text-left text-xs text-white/50">
          Email
          <input
            type="email"
            name="email"
            required
            placeholder="you@lab.org"
            className="mt-1.5 w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2.5 text-sm text-white/90 placeholder-white/30 outline-none ring-violet-500/30 focus:border-violet-500/40 focus:ring-1"
          />
        </label>
        <label className="block text-left text-xs text-white/50">
          Message
          <textarea
            name="message"
            rows={4}
            placeholder="Brief note…"
            className="mt-1.5 w-full resize-y rounded-lg border border-white/10 bg-black/20 px-3 py-2.5 text-sm text-white/90 placeholder-white/30 outline-none ring-violet-500/30 focus:border-violet-500/40 focus:ring-1"
          />
        </label>
        <button
          type="submit"
          className="w-full rounded-lg bg-gradient-to-r from-violet-500 to-indigo-600 py-2.5 text-sm font-semibold text-white shadow-[0_0_24px_rgba(139,92,246,0.3)] transition hover:scale-[1.02] active:scale-[0.99]"
        >
          {sent ? 'Noted (demo)' : 'Send'}
        </button>
      </form>
    </SectionShell>
  )
}
