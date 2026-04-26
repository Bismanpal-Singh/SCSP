import { useEffect, useMemo, useRef, useState } from 'react'
import { fetchStructureByFormula, fetchStructureByMpId } from '../api/structureClient'

let scriptPromise = null

function ensure3DmolLoaded() {
  if (window.$3Dmol) return Promise.resolve(window.$3Dmol)
  if (scriptPromise) return scriptPromise

  scriptPromise = new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.1.0/3Dmol-min.js'
    script.async = true
    script.onload = () => resolve(window.$3Dmol)
    script.onerror = () => reject(new Error('Failed to load 3D viewer library'))
    document.head.appendChild(script)
  })

  return scriptPromise
}

function structureToXyz(structure) {
  const sites = Array.isArray(structure?.sites) ? structure.sites : []
  if (!sites.length) return null

  const atomLines = sites
    .map((site) => {
      const specie = site?.label
        || site?.species?.[0]?.element
        || site?.species?.[0]?.name
        || site?.species?.[0]?.symbol
        || 'X'
      const xyz = Array.isArray(site?.xyz) ? site.xyz : []
      if (xyz.length !== 3) return null
      const [x, y, z] = xyz.map((value) => Number(value))
      if (![x, y, z].every(Number.isFinite)) return null
      return `${specie} ${x.toFixed(6)} ${y.toFixed(6)} ${z.toFixed(6)}`
    })
    .filter(Boolean)

  if (!atomLines.length) return null
  return `${atomLines.length}\nGenerated from Materials Project structure payload\n${atomLines.join('\n')}`
}

export default function StructureViewer({
  mpId,
  formula,
  width = 320,
  height = 300,
  showName = true,
  showStatusText = true,
}) {
  const containerRef = useRef(null)
  const [entry, setEntry] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const identity = useMemo(() => mpId || formula || '', [mpId, formula])

  useEffect(() => {
    let cancelled = false
    async function load() {
      if (!identity) return
      setLoading(true)
      setError(null)
      try {
        const data = mpId ? await fetchStructureByMpId(mpId) : await fetchStructureByFormula(formula)
        if (!cancelled) setEntry(data)
      } catch (err) {
        if (!cancelled) setError(err.message || 'Could not load structure')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [formula, identity, mpId])

  useEffect(() => {
    let mounted = true
    async function renderStructure() {
      if ((!entry?.cif && !entry?.structure) || !containerRef.current) return
      const threeDMol = await ensure3DmolLoaded()
      if (!mounted || !threeDMol || !containerRef.current) return

      const viewer = threeDMol.createViewer(containerRef.current, {
        backgroundColor: '#0b1325',
      })
      viewer.clear()
      if (entry.cif) {
        viewer.addModel(entry.cif, 'cif')
      } else if (entry.structure) {
        const xyzText = structureToXyz(entry.structure)
        if (!xyzText) throw new Error('Structure coordinates unavailable for rendering')
        viewer.addModel(xyzText, 'xyz')
      }
      viewer.setStyle({}, {
        stick: { radius: 0.2, colorscheme: 'Jmol' },
        sphere: { scale: 0.3, colorscheme: 'Jmol' },
      })
      viewer.addUnitCell()
      viewer.zoomTo()
      viewer.render()
    }
    renderStructure().catch((err) => setError(err.message || 'Viewer failed to render'))
    return () => { mounted = false }
  }, [entry])

  return (
    <div className="w-full">
      {showName && (
        <p className="mb-2 font-mono text-xs text-violet-200/80">
          {entry?.formula || formula || mpId || 'Material'}
        </p>
      )}
      <div
        ref={containerRef}
        style={{ width, height, position: 'relative', overflow: 'hidden' }}
        className="rounded-lg border border-violet-400/20 bg-[#0b1325]"
      />
      {showStatusText && loading && <p className="mt-2 font-mono text-[11px] text-white/60">Loading structure...</p>}
      {showStatusText && error && <p className="mt-2 text-xs text-rose-300/85">{error}</p>}
    </div>
  )
}
