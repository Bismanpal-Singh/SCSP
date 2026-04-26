import React from 'react'

export default function HypothesisInput({ value, onChange, onRun, disabled }) {
  function handleKey(e) {
    if (e.key === 'Enter' && !e.shiftKey && !disabled) {
      e.preventDefault()
      onRun()
    }
  }

  return (
    <div style={{ width: '100%' }}>
      <div style={{ display: 'flex', gap: 12, alignItems: 'stretch', flexWrap: 'wrap', width: '100%' }}>
        <textarea
          value={value}
          onChange={e => onChange(e.target.value)}
          onKeyDown={handleKey}
          disabled={disabled}
          placeholder="type here"
          rows={2}
          style={{
            flex: '1 1 100%',
            width: '100%',
            minWidth: 0,
            background: disabled ? 'rgba(10,10,12,0.5)' : 'var(--surface)',
            border: '1px solid',
            borderColor: disabled ? 'var(--border-dim)' : 'var(--border)',
            borderRadius: 10,
            padding: '14px 16px',
            color: disabled ? 'var(--text-muted)' : 'var(--text)',
            fontSize: 15,
            fontFamily: 'var(--font-sans)',
            lineHeight: 1.5,
            resize: 'vertical',
            minHeight: 52,
            outline: 'none',
            transition: 'border-color 0.2s, box-shadow 0.2s',
            cursor: disabled ? 'not-allowed' : 'text',
          }}
          onFocus={e => {
            if (!disabled) {
              e.target.style.borderColor = 'var(--neon)'
              e.target.style.boxShadow = '0 0 0 1px rgba(192, 132, 252, 0.35), 0 0 24px rgba(168, 85, 247, 0.12)'
            }
          }}
          onBlur={e => {
            e.target.style.borderColor = 'var(--border)'
            e.target.style.boxShadow = 'none'
          }}
        />

        <button
          type="button"
          onClick={onRun}
          disabled={disabled || !value.trim()}
          style={{
            background:
              disabled || !value.trim()
                ? 'rgba(168, 85, 247, 0.12)'
                : 'linear-gradient(145deg, var(--neon-bright) 0%, var(--p2) 50%, var(--p4) 100%)',
            color: disabled || !value.trim() ? 'rgba(192, 132, 252, 0.35)' : '#fff',
            border: 'none',
            borderRadius: 10,
            padding: '0 26px',
            fontFamily: 'var(--font-sans)',
            fontSize: 14,
            fontWeight: 700,
            letterSpacing: '0.04em',
            cursor: disabled || !value.trim() ? 'not-allowed' : 'pointer',
            transition: 'opacity 0.2s, transform 0.15s',
            whiteSpace: 'nowrap',
            minWidth: 128,
            alignSelf: 'stretch',
            boxShadow: disabled || !value.trim() ? 'none' : '0 0 28px rgba(192, 132, 252, 0.25)',
          }}
        >
          {disabled ? 'Working…' : 'Run agent'}
        </button>
      </div>
    </div>
  )
}
