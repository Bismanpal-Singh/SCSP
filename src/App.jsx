import React, { useEffect } from 'react'
import Navbar from './components/Navbar'
import { useHashRoute } from './hooks/useHashRoute'
import HomePage from './pages/HomePage'
import FeaturesPage from './pages/FeaturesPage'
import AboutPage from './pages/AboutPage'
import ContactPage from './pages/ContactPage'

export const USE_MOCK = false

const ROUTES = new Set(['/', '/features', '/about', '/contact'])

function resolveView(path) {
  if (ROUTES.has(path)) {
    if (path === '/features') return 'features'
    if (path === '/about') return 'about'
    if (path === '/contact') return 'contact'
    return 'home'
  }
  return 'home'
}

export default function App() {
  const { path } = useHashRoute()
  const view = resolveView(path)

  useEffect(() => {
    window.scrollTo(0, 0)
  }, [path])

  return (
    <div className="relative min-h-screen bg-mantle-bg text-white">
      <div className="min-h-screen w-full">
        <Navbar />
        <main
          style={{
            width: '100%',
            maxWidth: 1600,
            margin: '0 auto',
            padding: '0 32px',
            boxSizing: 'border-box',
          }}
        >
          {view === 'home' && <HomePage useMock={USE_MOCK} />}
          {view === 'features' && <FeaturesPage />}
          {view === 'about' && <AboutPage />}
          {view === 'contact' && <ContactPage />}
        </main>
      </div>
    </div>
  )
}
