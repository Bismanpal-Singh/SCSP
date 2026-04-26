import { useEffect, useState } from 'react'
import StructureViewer from './StructureViewer'
import { fetchStructureByFormula, fetchStructureByMpId, generateDescription } from '../api/structureClient'

export default function MaterialDetailModal({ mpId, formula, onClose }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        let result = null
        if (mpId) {
          try {
            result = await fetchStructureByMpId(mpId)
          } catch (mpErr) {
            if (!formula) throw mpErr
          }
        }
        if (!result) {
          result = await fetchStructureByFormula(formula)
        }
        if (!cancelled) setData(result)
      } catch (err) {
        if (!cancelled) setError(err.message || 'Could not load material details')
      }
    }
    load()
    return () => { cancelled = true }
  }, [formula, mpId])

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const description = data ? generateDescription(data) : null

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 9999,
        background: 'rgba(8, 14, 26, 0.85)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
        animation: 'modalFade 200ms ease-out',
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          position: 'relative',
          width: '100%',
          maxWidth: 900,
          maxHeight: '90vh',
          background: 'rgba(13, 21, 38, 0.98)',
          border: '1px solid rgba(167, 139, 250, 0.3)',
          borderRadius: 14,
          overflow: 'hidden',
          display: 'grid',
          gridTemplateColumns: '380px 1fr',
          boxShadow: '0 24px 80px rgba(0, 0, 0, 0.6), 0 0 60px rgba(167, 139, 250, 0.12)',
        }}
      >
        <div
          style={{
            padding: 24,
            borderRight: '1px solid rgba(167, 139, 250, 0.15)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 16,
          }}
        >
          {(mpId || formula) && (
            <StructureViewer
              mpId={mpId}
              formula={formula}
              width={320}
              height={300}
              showName={false}
            />
          )}

          {data && (
            <div style={{ textAlign: 'center', width: '100%' }}>
              {data.commonName && (
                <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 22, fontWeight: 600, color: '#fff' }}>
                  {data.commonName}
                </div>
              )}
              <div
                style={{
                  fontFamily: 'JetBrains Mono, monospace',
                  fontSize: 16,
                  fontWeight: 700,
                  color: 'rgba(167, 139, 250, 0.95)',
                  marginTop: 4,
                }}
              >
                {prettyFormula(data.formula)}
              </div>
              {data.family && (
                <div
                  style={{
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: 10,
                    color: 'rgba(167, 139, 250, 0.55)',
                    marginTop: 6,
                    letterSpacing: '0.1em',
                    textTransform: 'uppercase',
                  }}
                >
                  {data.family}
                </div>
              )}
            </div>
          )}
        </div>

        <div
          style={{
            padding: 28,
            overflowY: 'auto',
            maxHeight: '90vh',
            color: '#e2e8f0',
          }}
        >
          <button
            onClick={onClose}
            style={{
              position: 'absolute',
              top: 18,
              right: 18,
              background: 'transparent',
              border: 'none',
              color: 'rgba(255,255,255,0.5)',
              fontSize: 24,
              cursor: 'pointer',
              width: 32,
              height: 32,
              borderRadius: 6,
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.08)' }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent' }}
          >
            ×
          </button>

          {error && (
            <div style={{ color: '#f87171', padding: 20 }}>
              <div style={{ fontWeight: 700, marginBottom: 6 }}>Couldn&apos;t load material details</div>
              <div style={{ fontSize: 13, opacity: 0.8 }}>{error}</div>
            </div>
          )}

          {!error && data && (
            <>
              <div
                style={{
                  fontFamily: 'JetBrains Mono, monospace',
                  fontSize: 11,
                  color: 'rgba(167, 139, 250, 0.7)',
                  letterSpacing: '0.14em',
                  textTransform: 'uppercase',
                  marginBottom: 8,
                }}
              >
                // material details · {data.mpId}
              </div>

              <h2
                style={{
                  fontFamily: 'Inter, sans-serif',
                  fontSize: 26,
                  fontWeight: 700,
                  color: '#fff',
                  margin: 0,
                  marginBottom: 18,
                  letterSpacing: '-0.01em',
                }}
              >
                {data.commonName || prettyFormula(data.formula)}
              </h2>

              <div
                style={{
                  padding: 16,
                  borderRadius: 8,
                  background: 'rgba(167, 139, 250, 0.05)',
                  border: '1px solid rgba(167, 139, 250, 0.15)',
                  marginBottom: 22,
                  fontSize: 14,
                  lineHeight: 1.65,
                  color: 'rgba(226, 232, 240, 0.9)',
                }}
              >
                {description}
              </div>

              <PropertyGrid data={data} />

              <a
                href={data.mpUrl}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 8,
                  marginTop: 24,
                  padding: '11px 20px',
                  borderRadius: 8,
                  background: 'linear-gradient(135deg, #00f5d4, #a78bfa)',
                  color: '#080e1a',
                  fontFamily: 'JetBrains Mono, monospace',
                  fontSize: 12,
                  fontWeight: 700,
                  letterSpacing: '0.06em',
                  textDecoration: 'none',
                  transition: 'transform 0.15s, box-shadow 0.15s',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = 'translateY(-1px)'
                  e.currentTarget.style.boxShadow = '0 8px 24px rgba(0, 245, 212, 0.3)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'none'
                  e.currentTarget.style.boxShadow = 'none'
                }}
              >
                Open on Materials Project ↗
              </a>
            </>
          )}

          {!error && !data && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                minHeight: 300,
                color: 'rgba(167, 139, 250, 0.6)',
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 12,
                letterSpacing: '0.1em',
              }}
            >
              LOADING DETAILS...
            </div>
          )}
        </div>
      </div>

      <style>{'@keyframes modalFade { from { opacity: 0 } to { opacity: 1 } }'}</style>
    </div>
  )
}

function PropertyGrid({ data }) {
  const props = []
  if (data.symmetry?.crystal_system) props.push(['Crystal system', data.symmetry.crystal_system])
  if (data.symmetry?.symbol) props.push(['Space group', data.symmetry.symbol])
  if (data.density) props.push(['Density', `${Number(data.density).toFixed(3)} g/cm³`])
  if (data.volume) props.push(['Cell volume', `${Number(data.volume).toFixed(2)} Å³`])
  if (data.nsites) props.push(['Atoms per cell', data.nsites])
  if (data.bandGap !== undefined && data.bandGap !== null) {
    const bandGap = Number(data.bandGap)
    props.push(['Band gap', Number.isFinite(bandGap) && bandGap < 0.1 ? 'Metallic (0 eV)' : `${bandGap.toFixed(3)} eV`])
  }
  if (data.formationEnergyPerAtom !== undefined && data.formationEnergyPerAtom !== null) {
    props.push(['Formation energy', `${Number(data.formationEnergyPerAtom).toFixed(3)} eV/atom`])
  }
  if (data.energyAboveHull !== undefined && data.energyAboveHull !== null) {
    props.push(['Hull distance', `${Number(data.energyAboveHull).toFixed(3)} eV/atom`])
  }
  if (data.isStable !== undefined) props.push(['Stability', data.isStable ? '✓ Stable' : '○ Metastable'])
  if (data.isMagnetic !== undefined) props.push(['Magnetic', data.isMagnetic ? `✓ ${data.magneticOrdering || 'Yes'}` : 'No'])
  if (data.totalMagnetization !== undefined && data.totalMagnetization !== null) {
    props.push(['Magnetization', `${Number(data.totalMagnetization).toFixed(2)} μB/f.u.`])
  }
  if (data.theoretical !== undefined) {
    props.push(['Source', data.theoretical ? 'DFT calculation' : 'Experimentally observed'])
  }

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: 1,
        background: 'rgba(167, 139, 250, 0.15)',
        border: '1px solid rgba(167, 139, 250, 0.15)',
        borderRadius: 8,
        overflow: 'hidden',
      }}
    >
      {props.map(([label, value], i) => (
        <div
          key={`${label}-${i}`}
          style={{
            padding: '12px 16px',
            background: 'rgba(13, 21, 38, 0.95)',
            display: 'flex',
            flexDirection: 'column',
            gap: 4,
          }}
        >
          <span
            style={{
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: 10,
              color: 'rgba(167, 139, 250, 0.6)',
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
            }}
          >
            {label}
          </span>
          <span
            style={{
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: 13,
              color: '#fff',
              fontWeight: 600,
            }}
          >
            {value}
          </span>
        </div>
      ))}
    </div>
  )
}

function prettyFormula(formula = '') {
  const subs = { 0: '₀', 1: '₁', 2: '₂', 3: '₃', 4: '₄', 5: '₅', 6: '₆', 7: '₇', 8: '₈', 9: '₉' }
  return String(formula).replace(/\d/g, (digit) => subs[digit] || digit)
}
