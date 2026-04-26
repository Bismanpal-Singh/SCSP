import React from 'react'

const link = {
  fontSize: 13,
  fontWeight: 500,
  color: 'var(--text-dim)',
  textDecoration: 'none',
  transition: 'color 0.15s',
  cursor: 'pointer',
}
const linkHover = (e) => { e.currentTarget.style.color = 'var(--neon)' }
const linkLeave = (e) => { e.currentTarget.style.color = 'var(--text-dim)' }
const noop = (e) => e.preventDefault()

export default function Header() {
  return (
    <header
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 100,
        background: 'rgba(0,0,0,0.85)',
        backdropFilter: 'blur(10px)',
        borderBottom: '1px solid var(--border)',
        padding: '0 24px 0 20px',
        minHeight: 56,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}
    >
      {/* Left — logo */}
      <a
        href="/"
        style={{ display: 'flex', alignItems: 'center', gap: 12, textDecoration: 'none' }}
      >
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: 8,
            background: 'linear-gradient(135deg, var(--neon) 0%, var(--p4) 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 20px rgba(192, 132, 252, 0.35)',
            flexShrink: 0,
          }}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
            <path
              d="M4 20V4l4 8 4-8 4 8 4-8v16h-2.5V9.2L15 16l-3.5-7L8 16l-4-6.8V20H4Z"
              fill="#0a0a0c"
            />
          </svg>
        </div>
      </a>

      {/* Right — nav */}
      <nav style={{ display: 'flex', alignItems: 'center', gap: 28 }}>
        <a href="#about" style={link} onClick={noop} onMouseEnter={linkHover} onMouseLeave={linkLeave}>
          About
        </a>
        <a href="#contact" style={link} onClick={noop} onMouseEnter={linkHover} onMouseLeave={linkLeave}>
          Contact
        </a>
      </nav>
    </header>
  )
}
