import React from 'react'

function LogoMark() {
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden
      className="text-violet-400"
    >
      <path
        d="M12 2L4 8v8l8 6 8-6V8l-8-6z"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinejoin="round"
        className="opacity-90"
      />
      <path d="M12 2v20M4 8l16 8M20 8L4 16" stroke="currentColor" strokeWidth="0.6" opacity="0.45" />
      <circle cx="12" cy="12" r="2" fill="currentColor" className="opacity-60" />
    </svg>
  )
}

const nav = [
  { href: '#/features', label: 'Features' },
  { href: '#/about', label: 'About' },
  { href: '#/contact', label: 'Contact' },
]

export default function Navbar() {
  const currentHash = typeof window === 'undefined' ? '#/' : window.location.hash || '#/'

  return (
    <header className="sticky top-0 z-30 border-b border-white/[0.06] bg-[#0a0a0f]/70 backdrop-blur-xl">
      <div
        className="pointer-events-none absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-transparent via-violet-500/35 to-transparent shadow-[0_0_20px_rgba(139,92,246,0.25)]"
        aria-hidden
      />
      <div className="relative mx-auto flex h-14 max-w-6xl items-center justify-between px-4 sm:h-16 sm:px-6 lg:px-8">
        <a
          href="#/"
          className="group flex items-center gap-3 text-white no-underline transition-opacity hover:opacity-95"
        >
          <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/10 bg-white/[0.04] shadow-[0_0_24px_rgba(139,92,246,0.12)] ring-1 ring-violet-500/20 transition group-hover:border-violet-500/30 group-hover:shadow-[0_0_28px_rgba(139,92,246,0.2)]">
            <LogoMark />
          </span>
          <span className="font-semibold tracking-tight text-white/95">Mantle AI</span>
        </a>
        <nav className="flex items-center gap-5 sm:gap-7" aria-label="Primary">
          {nav.map((item) => (
            <a
              key={item.href}
              href={item.href}
              className={[
                'text-sm font-medium transition-colors hover:text-violet-300',
                currentHash === item.href
                  ? 'text-violet-300 drop-shadow-[0_0_10px_rgba(139,92,246,0.35)]'
                  : 'text-white/55',
              ].join(' ')}
            >
              {item.label}
            </a>
          ))}
        </nav>
      </div>
    </header>
  )
}
