import React, { useEffect, useState } from 'react'

const MESSAGES = [
  'Analyzing material space…',
  'Evaluating candidate structures…',
  'Optimizing composition…',
  'Finalizing results…',
]

const ROTATE_MS = 1600

/**
 * Rotates status copy on an interval; crossfades with opacity for a soft “live” feel.
 */
export default function StatusText() {
  const [index, setIndex] = useState(0)
  const [visible, setVisible] = useState(true)

  useEffect(() => {
    const id = window.setInterval(() => {
      setVisible(false)
      window.setTimeout(() => {
        setIndex((i) => (i + 1) % MESSAGES.length)
        setVisible(true)
      }, 220)
    }, ROTATE_MS)
    return () => clearInterval(id)
  }, [])

  return (
    <p
      className="min-h-[1.4em] text-center text-sm font-medium text-violet-200/90 sm:text-base"
      style={{ transition: 'opacity 0.25s ease-in-out' }}
    >
      <span
        className="inline-block"
        style={{ opacity: visible ? 1 : 0, transition: 'opacity 0.25s ease-in-out' }}
      >
        {MESSAGES[index]}
      </span>
    </p>
  )
}
