import React from 'react'

export default function MarkdownText({ text, style = {} }) {
  if (!text) return null

  const cleaned = String(text || '').trim()
  const blocks = parseBlocks(cleaned)

  return (
    <div
      style={{
        fontFamily: 'Inter, sans-serif',
        fontSize: 14.5,
        lineHeight: 1.7,
        color: 'var(--text-dim, #cbd5e1)',
        ...style,
      }}
    >
      {blocks.map((block, i) => renderBlock(block, i))}
    </div>
  )
}

function parseBlocks(text) {
  const lines = text.split('\n').map((line) => line.trim())
  const blocks = []
  let currentList = null
  let paragraph = []

  const flushParagraph = () => {
    if (paragraph.length) {
      blocks.push({ type: 'paragraph', text: paragraph.join(' ') })
      paragraph = []
    }
  }
  const flushList = () => {
    if (currentList) {
      blocks.push(currentList)
      currentList = null
    }
  }

  for (const line of lines) {
    if (!line) {
      flushParagraph()
      flushList()
      continue
    }

    const headingMatch = line.match(/^(\d+)[.)]\s+(.+)$/)
    if (headingMatch && headingMatch[2].length < 100) {
      flushParagraph()
      flushList()
      blocks.push({ type: 'heading', num: headingMatch[1], text: headingMatch[2] })
      continue
    }

    const bulletMatch = line.match(/^[-•*]\s+(.+)$/)
    if (bulletMatch) {
      flushParagraph()
      if (!currentList) currentList = { type: 'list', items: [] }
      currentList.items.push(bulletMatch[1])
      continue
    }

    flushList()
    paragraph.push(line)
  }

  flushParagraph()
  flushList()
  return blocks
}

function renderBlock(block, key) {
  if (block.type === 'heading') {
    return (
      <h4
        key={key}
        style={{
          fontFamily: 'Inter, sans-serif',
          fontSize: 15,
          fontWeight: 700,
          color: '#fff',
          margin: '20px 0 8px 0',
          letterSpacing: '-0.005em',
        }}
      >
        <span
          style={{
            color: 'rgba(167, 139, 250, 0.9)',
            marginRight: 8,
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 13,
          }}
        >
          {block.num}.
        </span>
        {renderInline(block.text)}
      </h4>
    )
  }

  if (block.type === 'list') {
    return (
      <ul
        key={key}
        style={{
          margin: '8px 0 14px 0',
          paddingLeft: 0,
          listStyle: 'none',
        }}
      >
        {block.items.map((item, j) => (
          <li
            key={`${j}-${item}`}
            style={{
              padding: '4px 0',
              paddingLeft: 22,
              position: 'relative',
            }}
          >
            <span
              style={{
                position: 'absolute',
                left: 4,
                top: '0.55em',
                width: 6,
                height: 6,
                borderRadius: '50%',
                background: 'rgba(167, 139, 250, 0.7)',
              }}
            />
            {renderInline(item)}
          </li>
        ))}
      </ul>
    )
  }

  if (block.type === 'paragraph') {
    return (
      <p key={key} style={{ margin: '0 0 12px 0' }}>
        {renderInline(block.text)}
      </p>
    )
  }

  return null
}

function renderInline(text) {
  if (!text) return null

  const parts = []
  const regex = /\*\*([^*]+)\*\*/g
  let lastIndex = 0
  let match
  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ type: 'text', value: text.slice(lastIndex, match.index) })
    }
    parts.push({ type: 'bold', value: match[1] })
    lastIndex = regex.lastIndex
  }
  if (lastIndex < text.length) {
    parts.push({ type: 'text', value: text.slice(lastIndex) })
  }

  return parts.map((part, i) => {
    if (part.type === 'bold') {
      return (
        <strong key={`b-${i}`} style={{ color: '#fff', fontWeight: 700 }}>
          {part.value}
        </strong>
      )
    }
    return <React.Fragment key={`t-${i}`}>{prettifyFormulas(part.value)}</React.Fragment>
  })
}

function prettifyFormulas(text) {
  return String(text).replace(/\b([A-Z][a-z]?\d+(?:[A-Z][a-z]?\d*)+)\b/g, (match) => {
    const subs = { 0: '₀', 1: '₁', 2: '₂', 3: '₃', 4: '₄', 5: '₅', 6: '₆', 7: '₇', 8: '₈', 9: '₉' }
    return match.replace(/\d/g, (digit) => subs[digit] || digit)
  })
}
