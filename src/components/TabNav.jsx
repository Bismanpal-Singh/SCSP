import React from 'react'

const TABS = [
  { label: 'Agent at Work',      dot: 'var(--neon)',  num: '01' },
  { label: 'Results Dashboard',  dot: 'var(--p2)',    num: '02' },
  { label: 'Agent Decision Log', dot: 'var(--p4)',    num: '03' },
]

export default function TabNav({ activeTab, onTabChange }) {
  return (
    <div style={{
      display: 'flex',
      borderBottom: '1px solid var(--border)',
      gap: 0,
    }}>
      {TABS.map((tab, i) => {
        const isActive = activeTab === i
        return (
          <button
            key={i}
            onClick={() => onTabChange(i)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 9,
              padding: '12px 22px',
              background: 'transparent',
              border: 'none',
              borderBottom: isActive
                ? `2px solid ${tab.dot}`
                : '2px solid transparent',
              marginBottom: -1,
              color: isActive ? '#fff' : 'var(--text-muted)',
              cursor: 'pointer',
              fontSize: 13.5,
              fontFamily: 'var(--font-sans)',
              fontWeight: isActive ? 600 : 400,
              transition: 'all 0.15s',
              whiteSpace: 'nowrap',
            }}
            onMouseEnter={e => { if (!isActive) e.currentTarget.style.color = 'var(--text-dim)' }}
            onMouseLeave={e => { if (!isActive) e.currentTarget.style.color = 'var(--text-muted)' }}
          >
            {/* Dot */}
            <span style={{
              width: 7, height: 7,
              borderRadius: '50%',
              background: isActive ? tab.dot : 'var(--border)',
              flexShrink: 0,
              transition: 'background 0.15s',
            }} />

            {/* Number */}
            <span style={{
              fontFamily: 'var(--font-mono)',
              fontSize: 10,
              color: isActive ? tab.dot : 'var(--text-muted)',
              letterSpacing: '0.06em',
            }}>
              {tab.num}
            </span>

            {/* Label */}
            {tab.label}
          </button>
        )
      })}
    </div>
  )
}
