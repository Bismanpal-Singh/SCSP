import { useState } from 'react'
import MaterialDetailModal from './MaterialDetailModal'

export default function MaterialLink({ mpId, formula, children, bare = false, style = {} }) {
  const [open, setOpen] = useState(false)

  const linkStyle = bare
    ? style
    : {
      cursor: 'pointer',
      textDecoration: 'none',
      borderBottom: '1px dotted rgba(167, 139, 250, 0.5)',
      color: 'inherit',
      transition: 'all 0.15s',
      ...style,
    }

  const canOpen = Boolean(mpId || formula)

  return (
    <>
      <span
        role={canOpen ? 'button' : undefined}
        tabIndex={canOpen ? 0 : undefined}
        onClick={(e) => {
          e.stopPropagation()
          if (canOpen) setOpen(true)
        }}
        onKeyDown={(e) => {
          if (!canOpen) return
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            setOpen(true)
          }
        }}
        style={linkStyle}
        onMouseEnter={(e) => {
          if (bare || !canOpen) return
          e.currentTarget.style.borderBottomColor = 'rgba(167, 139, 250, 1)'
          e.currentTarget.style.borderBottomStyle = 'solid'
          e.currentTarget.style.color = '#a78bfa'
        }}
        onMouseLeave={(e) => {
          if (bare || !canOpen) return
          e.currentTarget.style.borderBottomColor = 'rgba(167, 139, 250, 0.5)'
          e.currentTarget.style.borderBottomStyle = 'dotted'
          e.currentTarget.style.color = 'inherit'
        }}
      >
        {children}
      </span>

      {open && (
        <MaterialDetailModal
          mpId={mpId}
          formula={formula}
          onClose={() => setOpen(false)}
        />
      )}
    </>
  )
}
