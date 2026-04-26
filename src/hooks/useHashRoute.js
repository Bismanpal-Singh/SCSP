import { useCallback, useSyncExternalStore } from 'react'

/**
 * Path from location.hash, e.g. #/ → /, #/features → /features.
 * Stays in sync for browser back/forward; no server rewrite needed.
 */
function getPath() {
  const h = window.location.hash
  if (!h || h === '#') return '/'
  const raw = h.slice(1)
  if (!raw) return '/'
  return raw.startsWith('/') ? raw : `/${raw}`
}

function subscribe(fn) {
  window.addEventListener('hashchange', fn)
  return () => window.removeEventListener('hashchange', fn)
}

export function useHashRoute() {
  const path = useSyncExternalStore(subscribe, getPath, () => '/')
  const go = useCallback((p) => {
    window.location.hash = p === '/' ? '' : p
  }, [])
  return { path, go }
}
