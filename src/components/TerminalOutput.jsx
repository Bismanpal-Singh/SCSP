import React, { useEffect, useRef, useState } from 'react'

const BOOT_LINE = '> Running Mantle AI...\n\n'
const STREAM_DELAY_MS = 14
const START_DELAY_MS = 500

/**
 * Streams raw agent text into a polished terminal surface.
 * Keeps spacing/line breaks intact and auto-scrolls as new text arrives.
 */
export default function TerminalOutput({ output, onReset }) {
  const [visibleText, setVisibleText] = useState(BOOT_LINE)
  const scrollRef = useRef(null)

  useEffect(() => {
    setVisibleText(BOOT_LINE)
    let index = 0
    let intervalId

    const startId = window.setTimeout(() => {
      intervalId = window.setInterval(() => {
        index += 1
        setVisibleText(BOOT_LINE + output.slice(0, index))
        if (index >= output.length) {
          window.clearInterval(intervalId)
        }
      }, STREAM_DELAY_MS)
    }, START_DELAY_MS)

    return () => {
      window.clearTimeout(startId)
      window.clearInterval(intervalId)
    }
  }, [output])

  useEffect(() => {
    if (!scrollRef.current) return
    scrollRef.current.scrollTop = scrollRef.current.scrollHeight
  }, [visibleText])

  return (
    <div className="mx-auto w-full max-w-3xl opacity-0 animate-fade-in">
      <div className="overflow-hidden rounded-2xl border border-violet-500/20 bg-[#050509]/90 shadow-[0_0_44px_rgba(139,92,246,0.12),inset_0_1px_0_rgba(255,255,255,0.05)] backdrop-blur-xl">
        <div className="flex items-center justify-between border-b border-white/[0.07] bg-white/[0.035] px-4 py-3">
          <div className="flex items-center gap-2" aria-hidden>
            <span className="h-2.5 w-2.5 rounded-full bg-red-400/80" />
            <span className="h-2.5 w-2.5 rounded-full bg-yellow-300/80" />
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-400/80" />
          </div>
          <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-white/35">
            Mantle AI Terminal
          </span>
          {onReset ? (
            <button
              type="button"
              onClick={onReset}
              className="font-mono text-[10px] uppercase tracking-[0.16em] text-violet-300/70 transition hover:text-violet-200"
            >
              New
            </button>
          ) : (
            <span className="w-8" aria-hidden />
          )}
        </div>

        <div
          ref={scrollRef}
          className="max-h-[52vh] min-h-[280px] overflow-y-auto px-4 py-5 text-left font-mono text-[12px] leading-6 text-white/78 sm:px-6 sm:py-6 sm:text-[13px]"
        >
          <pre className="whitespace-pre-wrap break-words font-mono">
            {visibleText}
            <span className="ml-0.5 inline-block h-4 w-2 translate-y-0.5 bg-violet-300/80 animate-[terminalBlink_1s_steps(2,start)_infinite]" />
          </pre>
        </div>
      </div>
      <style>{`
        @keyframes terminalBlink {
          0%, 45% { opacity: 1; }
          46%, 100% { opacity: 0; }
        }
      `}</style>
    </div>
  )
}
