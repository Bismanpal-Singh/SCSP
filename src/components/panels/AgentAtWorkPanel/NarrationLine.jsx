import React from 'react'
import { motion } from 'framer-motion'

function toneClass(tone) {
  if (tone === 'pivot') return 'text-cyan-200'
  if (tone === 'reject') return 'text-rose-200/90'
  if (tone === 'success') return 'text-emerald-200'
  return 'text-white/86'
}

export default function NarrationLine({ isActive = false, text, tone = 'default' }) {
  return (
    <motion.p
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
      className={[
        'relative pl-6 text-[15px] leading-[1.6] transition-colors duration-500',
        toneClass(tone),
        isActive ? '' : 'opacity-80',
      ].join(' ')}
    >
      {isActive && (
        <span
          className="absolute left-0 top-[0.58em] h-2 w-2 rounded-full bg-cyan-300 shadow-[0_0_16px_rgba(34,211,238,0.85)] animate-pulse"
          aria-hidden
        />
      )}
      {text}
    </motion.p>
  )
}
