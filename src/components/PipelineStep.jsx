import React from 'react'

function IconSpark() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" aria-hidden>
      <path
        d="M12 2l1.2 4.2L17 8l-3.8 1.8L12 14l-1.2-4.2L7 8l4.2-1.8L12 2z"
        fill="currentColor"
        className="opacity-90"
      />
    </svg>
  )
}
function IconDb() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" aria-hidden>
      <ellipse cx="12" cy="6" rx="8" ry="3" stroke="currentColor" strokeWidth="1.2" />
      <path d="M4 6v6c0 1.7 3.6 3 8 3s8-1.3 8-3V6" stroke="currentColor" strokeWidth="1.2" />
      <path d="M4 12v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6" stroke="currentColor" strokeWidth="1.2" />
    </svg>
  )
}
function IconAtom() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" aria-hidden>
      <circle cx="12" cy="12" r="2" fill="currentColor" />
      <ellipse cx="12" cy="12" rx="9" ry="4" stroke="currentColor" strokeWidth="0.8" opacity="0.5" />
      <ellipse
        cx="12"
        cy="12"
        rx="9"
        ry="4"
        stroke="currentColor"
        strokeWidth="0.8"
        opacity="0.4"
        transform="rotate(60 12 12)"
      />
    </svg>
  )
}
function IconTune() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" aria-hidden>
      <path
        d="M4 6h4M10 6h2M4 12h8M20 8v8M4 18h6M14 18h2"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
      />
      <circle cx="16" cy="6" r="2" stroke="currentColor" strokeWidth="1.2" />
      <circle cx="16" cy="12" r="2" stroke="currentColor" strokeWidth="1.2" />
      <circle cx="10" cy="18" r="2" stroke="currentColor" strokeWidth="1.2" />
    </svg>
  )
}
function IconRank() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" aria-hidden>
      <path
        d="M8 8h8v2H8V8zM5 4h2v12H5V4zM9 4h2v9H9V4zM18 4h1v6h-1V4zM13 11h2v5h-2v-5zM17 4h-2v3h2V4z"
        fill="currentColor"
        className="opacity-85"
      />
    </svg>
  )
}
function IconCheck() {
  return (
    <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" aria-hidden>
      <path
        d="M5 12l4 4 8-8"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="text-emerald-300"
      />
    </svg>
  )
}

const ICONS = { spark: IconSpark, db: IconDb, atom: IconAtom, tune: IconTune, rank: IconRank }

/**
 * @param {'upcoming' | 'active' | 'complete'} state
 */
export default function PipelineStep({ title, subtitle, icon = 'atom', state = 'upcoming' }) {
  const Icon = ICONS[icon] || IconAtom
  const isDone = state === 'complete'
  const isActive = state === 'active'
  const isUp = state === 'upcoming'

  return (
    <div
      className={[
        'relative flex w-full flex-col items-center rounded-xl border px-3 py-2.5 text-center transition-all duration-500 ease-in-out sm:min-w-[7.5rem] sm:max-w-[9rem] sm:py-3',
        isUp
          ? 'border-white/[0.08] bg-white/[0.02] text-white/40'
          : isActive
            ? 'scale-[1.045] border-violet-400/50 bg-violet-500/10 text-white shadow-[0_0_32px_rgba(139,92,246,0.45),inset_0_0_20px_rgba(139,92,246,0.12)]'
            : 'border-violet-500/20 bg-violet-500/[0.07] text-white/80',
        isUp ? 'opacity-40' : isDone ? 'opacity-80' : 'opacity-100',
        isActive ? 'animate-pipeline-breathe' : '',
      ]
        .filter(Boolean)
        .join(' ')}
    >
      {isActive && (
        <span
          className="pointer-events-none absolute inset-0 -z-10 rounded-xl"
          style={{
            background: 'radial-gradient(ellipse at 50% 0%, rgba(139, 92, 246, 0.35) 0%, transparent 70%)',
          }}
          aria-hidden
        />
      )}
      <div
        className={[
          'mb-1 flex h-7 w-7 items-center justify-center rounded-lg',
          isUp ? 'text-white/35' : isActive ? 'text-violet-200' : 'text-violet-300/80',
        ].join(' ')}
      >
        {isDone ? <IconCheck /> : <Icon />}
      </div>
      <h4 className="text-[10px] font-semibold leading-tight sm:text-xs">{title}</h4>
      {subtitle && (
        <p className="mt-0.5 line-clamp-2 text-[9px] leading-snug text-white/45 sm:text-[10px]">
          {subtitle}
        </p>
      )}
    </div>
  )
}
