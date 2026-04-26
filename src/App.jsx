import React, { useCallback, useEffect, useState } from 'react'
import BackgroundEffect from './components/BackgroundEffect'
import Cursor from './components/Cursor'
import IntroLoader from './components/IntroLoader'
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
  const [introPhase, setIntroPhase] = useState('intro')
  const [showIntro, setShowIntro] = useState(() => path === '/')
  const revealApp = introPhase === 'shatter' || introPhase === 'complete' || !showIntro

  useEffect(() => {
    window.scrollTo(0, 0)
  }, [path])

  useEffect(() => {
    if (path !== '/') {
      setShowIntro(false)
      setIntroPhase('complete')
    }
  }, [path])

  const handleIntroComplete = useCallback(() => {
    setShowIntro(false)
    setIntroPhase('complete')
  }, [])

  return (
    <div className="relative min-h-screen bg-mantle-bg text-white">
      <div
        className="min-h-screen transition-[opacity,filter,transform] duration-700 ease-out"
        style={{
          opacity: revealApp ? 1 : 0,
          filter: revealApp ? 'blur(0px)' : 'blur(8px)',
          transform: revealApp ? 'scale(1)' : 'scale(0.99)',
        }}
      >
        <BackgroundEffect />
        <Cursor />
        <Navbar />
        {view === 'home' && <HomePage useMock={USE_MOCK} />}
        {view === 'features' && <FeaturesPage />}
        {view === 'about' && <AboutPage />}
        {view === 'contact' && <ContactPage />}
      </div>
      {showIntro && (
        <IntroLoader onPhaseChange={setIntroPhase} onComplete={handleIntroComplete} />
      )}
    </div>
  )
}
