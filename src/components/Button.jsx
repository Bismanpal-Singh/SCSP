import React from 'react'

/**
 * CTA: gradient, glow, scale on hover, press on active, shimmer when loading.
 * `isLoading` shows “Initializing…” and a moving highlight — parent clears after the simulated start.
 */
export default function Button({
  children = 'Run Agent',
  onClick,
  isLoading = false,
  /** Lower emphasis when query is empty; click still runs (e.g. shake) */
  isDimmed = false,
  /** sm = inline, fits label; md = full-width bar (legacy) */
  size = 'sm',
  type = 'button',
  className = '',
}) {
  const isBusy = isLoading

  const sizeClasses =
    size === 'md'
      ? 'mt-6 w-full px-6 py-3.5 text-sm sm:mt-8 sm:py-4 sm:text-base'
      : 'w-auto max-w-full whitespace-nowrap px-4 py-2 text-xs sm:px-5 sm:py-2.5 sm:text-sm'

  return (
    <button
      data-magnetic="true"
      type={type}
      onClick={onClick}
      disabled={isBusy}
      className={[
        'group relative inline-flex shrink-0 justify-center overflow-hidden rounded-lg font-semibold tracking-wide text-white transition-all duration-200',
        sizeClasses,
        'bg-gradient-to-r from-violet-500 via-violet-600 to-indigo-600',
        'shadow-[0_0_32px_rgba(139,92,246,0.35),inset_0_1px_0_rgba(255,255,255,0.12)]',
        'active:scale-[0.98] active:duration-100',
        isDimmed && !isBusy ? 'opacity-60 hover:opacity-85' : '',
        isBusy
          ? 'pointer-events-none cursor-wait opacity-100 animate-glow-pulse'
          : 'cursor-pointer hover:scale-[1.03] hover:shadow-[0_0_40px_rgba(139,92,246,0.5),inset_0_1px_0_rgba(255,255,255,0.15)]',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
    >
      {/* Shimmer sweep while loading — gradient mask animation */}
      {isBusy && (
        <span
          className="pointer-events-none absolute inset-0 bg-[length:200%_100%] opacity-30 animate-shimmer"
          style={{
            backgroundImage:
              'linear-gradient(105deg, transparent 40%, rgba(255,255,255,0.4) 50%, transparent 60%)',
          }}
          aria-hidden
        />
      )}
      <span className="relative z-10 flex items-center justify-center gap-2">
        {isBusy ? 'Initializing…' : children}
      </span>
    </button>
  )
}
