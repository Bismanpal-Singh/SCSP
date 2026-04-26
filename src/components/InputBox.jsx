import React, { useEffect, useRef, useState } from 'react'

/** Small crystal / atom mark inside the field */
function InputLeadingIcon() {
  return (
    <span className="pointer-events-none flex h-5 w-5 flex-shrink-0 text-violet-400/80" aria-hidden>
      <svg viewBox="0 0 24 24" fill="none" className="h-full w-full">
        <circle cx="12" cy="12" r="2.5" fill="currentColor" className="opacity-90" />
        <ellipse
          cx="12"
          cy="12"
          rx="9"
          ry="4"
          stroke="currentColor"
          strokeWidth="0.8"
          className="opacity-50"
          transform="rotate(0 12 12)"
        />
        <ellipse
          cx="12"
          cy="12"
          rx="9"
          ry="4"
          stroke="currentColor"
          strokeWidth="0.8"
          className="opacity-40"
          transform="rotate(60 12 12)"
        />
        <ellipse
          cx="12"
          cy="12"
          rx="9"
          ry="4"
          stroke="currentColor"
          strokeWidth="0.8"
          className="opacity-40"
          transform="rotate(120 12 12)"
        />
      </svg>
    </span>
  )
}

/**
 * Input behavior: Enter runs the same action as the primary button (passed via onEnter).
 * `shakeVersion` increments when parent wants a shake (e.g. empty submit) without remounting the field.
 */
export default function InputBox({
  value,
  onChange,
  onEnter,
  disabled = false,
  id = 'mantle-query',
  shakeVersion = 0,
}) {
  const inputRef = useRef(null)
  const [shaking, setShaking] = useState(false)

  useEffect(() => {
    if (shakeVersion === 0) return
    setShaking(true)
    const t = setTimeout(() => setShaking(false), 450)
    return () => clearTimeout(t)
  }, [shakeVersion])

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      onEnter()
    }
  }

  return (
    <div
      className={[
        'rounded-xl border border-violet-500/20 bg-white/[0.04] p-1 shadow-[inset_0_1px_0_rgba(255,255,255,0.05)] backdrop-blur-xl transition-[box-shadow,border-color] duration-300',
        'focus-within:border-violet-500/40 focus-within:shadow-[0_0_0_1px_rgba(139,92,246,0.45),0_0_32px_rgba(139,92,246,0.12),inset_0_0_20px_rgba(139,92,246,0.06)]',
        shaking ? 'animate-shake border-rose-500/25' : '',
        disabled ? 'pointer-events-none opacity-60' : '',
      ]
        .filter(Boolean)
        .join(' ')}
    >
      <label htmlFor={id} className="sr-only">
        Material discovery query
      </label>
      <div className="flex min-h-[52px] items-center gap-3 rounded-[10px] px-3 py-2.5 sm:px-4">
        <InputLeadingIcon />
        <input
          ref={inputRef}
          id={id}
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          autoComplete="off"
          placeholder="What material are you trying to discover or optimize?"
          className="min-w-0 flex-1 border-0 bg-transparent text-sm text-white/95 placeholder-white/32 outline-none ring-0 sm:text-base"
        />
        <span className="hidden flex-shrink-0 text-[10px] tracking-wide text-white/25 sm:inline sm:text-xs">
          Press Enter ↵
        </span>
      </div>
    </div>
  )
}
