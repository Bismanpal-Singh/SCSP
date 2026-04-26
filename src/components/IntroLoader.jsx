import React, { useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'

const SHATTER_START_MS = 3700
const SHATTER_ANIMATION_S = 3.2
const SHATTER_MAX_DELAY_S = 0.42
const OVERLAY_FADE_S = 0.45
const INTRO_COMPLETE_MS = SHATTER_START_MS + (SHATTER_ANIMATION_S + SHATTER_MAX_DELAY_S) * 1000 + 80
const UNMOUNT_MS = INTRO_COMPLETE_MS + OVERLAY_FADE_S * 1000

const letters = ['M', 'a', 'n', 't', 'l', 'e', 'A', 'I']

const letterFragments = [
  { char: 'M', x: -205, y: -118, tx: -330, ty: -160, rot: -34, delay: 0.04 },
  { char: 'a', x: -145, y: 4, tx: -245, ty: 190, rot: 42, delay: 0.22 },
  { char: 'n', x: -88, y: -7, tx: -130, ty: -280, rot: -66, delay: 0.11 },
  { char: 't', x: -34, y: 8, tx: -60, ty: 280, rot: 28, delay: 0.18 },
  { char: 'l', x: 18, y: -8, tx: 72, ty: -255, rot: -22, delay: 0.08 },
  { char: 'e', x: 68, y: 5, tx: 170, ty: 230, rot: 58, delay: 0.24 },
  { char: 'A', x: 145, y: -6, tx: 290, ty: -210, rot: 34, delay: 0.1, bold: true },
  { char: 'I', x: 211, y: 2, tx: 370, ty: 118, rot: -44, delay: 0.29, bold: true },
]

const crystalFragments = [
  { shape: 1, x: -118, y: -20, tx: -440, ty: -95, rot: -72, delay: 0.02 },
  { shape: 2, x: -78, y: 16, tx: -360, ty: 210, rot: 116, delay: 0.16 },
  { shape: 3, x: -12, y: -36, tx: -235, ty: -300, rot: -138, delay: 0.08 },
  { shape: 4, x: 40, y: 10, tx: -120, ty: 310, rot: 86, delay: 0.25 },
  { shape: 5, x: 96, y: -18, tx: 72, ty: -340, rot: -96, delay: 0.05 },
  { shape: 6, x: 142, y: 24, tx: 220, ty: 275, rot: 148, delay: 0.22 },
  { shape: 7, x: 4, y: 32, tx: 356, ty: -220, rot: -54, delay: 0.14 },
  { shape: 8, x: -160, y: 28, tx: -160, ty: 365, rot: 122, delay: 0.32 },
  { shape: 9, x: 170, y: -38, tx: 455, ty: -78, rot: 74, delay: 0.18 },
  { shape: 10, x: 36, y: -2, tx: 410, ty: 224, rot: -118, delay: 0.36 },
  { shape: 1, x: -22, y: 18, tx: -495, ty: 145, rot: 62, delay: 0.42 },
  { shape: 4, x: 118, y: 2, tx: 96, ty: -405, rot: -160, delay: 0.28 },
]

function useIntroSequence(onPhaseChange, onComplete) {
  const [phase, setPhase] = useState('intro')

  useEffect(() => {
    onPhaseChange?.('intro')
    const timers = [
      window.setTimeout(() => {
        setPhase('shatter')
        onPhaseChange?.('shatter')
      }, SHATTER_START_MS),
      window.setTimeout(() => {
        setPhase('complete')
        onPhaseChange?.('complete')
      }, INTRO_COMPLETE_MS),
      window.setTimeout(() => {
        onComplete?.()
      }, UNMOUNT_MS),
    ]
    return () => timers.forEach(clearTimeout)
  }, [onComplete, onPhaseChange])

  return phase
}

function Title() {
  return (
    <div className="intro-title-base select-none">
      <span className="font-extralight text-white">Mantle</span>
      <span className="ml-[0.15em] font-bold text-white">AI</span>
    </div>
  )
}

function LetterFragments() {
  return (
    <div className="intro-shatter-container" aria-hidden>
      {letterFragments.map((frag, index) => (
        <span
          key={`${frag.char}-${index}`}
          className="intro-letter-frag"
          style={{
            left: `calc(50% + ${frag.x}px)`,
            top: `calc(50% + ${frag.y}px)`,
            '--tx': `${frag.tx}px`,
            '--ty': `${frag.ty}px`,
            '--rot': `${frag.rot}deg`,
            animationDelay: `${frag.delay}s`,
            fontWeight: frag.bold ? 700 : 200,
          }}
        >
          {frag.char}
        </span>
      ))}
    </div>
  )
}

function CrystalFragments() {
  return (
    <div className="intro-shatter-container" aria-hidden>
      {crystalFragments.map((frag, index) => (
        <span
          key={`${frag.shape}-${index}`}
          className={`intro-fragment intro-frag-${frag.shape}`}
          style={{
            left: `calc(50% + ${frag.x}px)`,
            top: `calc(50% + ${frag.y}px)`,
            '--tx': `${frag.tx}px`,
            '--ty': `${frag.ty}px`,
            '--rot': `${frag.rot}deg`,
            animationDelay: `${frag.delay}s`,
          }}
        />
      ))}
    </div>
  )
}

function IntroStyles() {
  const css = useMemo(
    () => `
      .intro-title-base {
        font-family: 'Inter', system-ui, sans-serif;
        font-size: clamp(48px, 9vw, 120px);
        letter-spacing: -2px;
        color: #fff;
        opacity: 0;
        transform: scale(0.95);
        animation:
          introTitleAppear 1.2s cubic-bezier(0.22, 1, 0.36, 1) 0.3s forwards,
          introTitleGlow 2.4s ease-in-out 1.5s infinite,
          introTitleIntensify 0.6s ease-out 3.2s forwards;
      }

      @keyframes introTitleAppear {
        0% { opacity: 0; transform: scale(0.92); filter: blur(8px); }
        60% { opacity: 1; transform: scale(1.01); filter: blur(0); }
        100% { opacity: 1; transform: scale(1); filter: blur(0); }
      }

      @keyframes introTitleGlow {
        0%, 100% { text-shadow: 0 0 8px rgba(255, 255, 255, 0.15); }
        50% { text-shadow: 0 0 12px rgba(255, 255, 255, 0.25); }
      }

      @keyframes introTitleIntensify {
        0% { text-shadow: 0 0 12px rgba(255, 255, 255, 0.25); }
        100% {
          text-shadow:
            0 0 40px rgba(168, 92, 247, 0.8),
            0 0 80px rgba(139, 92, 246, 0.5),
            0 0 160px rgba(139, 92, 246, 0.3);
          transform: scale(1.05);
        }
      }

      .intro-shatter-active .intro-title-base {
        animation: introTitleHide 0.4s ease-out forwards;
      }

      @keyframes introTitleHide {
        to { opacity: 0; }
      }

      .intro-shatter-container {
        position: absolute;
        inset: 0;
        pointer-events: none;
      }

      .intro-letter-frag {
        position: absolute;
        transform: translate(-50%, -50%);
        font-family: 'Inter', system-ui, sans-serif;
        font-size: clamp(48px, 9vw, 120px);
        color: #fff;
        text-shadow: 0 0 20px rgba(168, 85, 247, 0.8);
        opacity: 0;
        pointer-events: none;
      }

      .intro-shatter-active .intro-letter-frag {
        animation: introLetterShatter ${SHATTER_ANIMATION_S}s cubic-bezier(0.23, 1, 0.32, 1) forwards;
      }

      @keyframes introLetterShatter {
        0% { opacity: 1; transform: translate(-50%, -50%) translate(0, 0) rotate(0deg) scale(1); filter: blur(0); }
        100% { opacity: 0; transform: translate(-50%, -50%) translate(var(--tx), var(--ty)) rotate(var(--rot)) scale(0.4); filter: blur(4px); }
      }

      .intro-fragment {
        position: absolute;
        transform: translate(-50%, -50%);
        background: linear-gradient(135deg, rgba(168, 85, 247, 0.7) 0%, rgba(139, 92, 246, 0.5) 50%, rgba(99, 102, 241, 0.3) 100%);
        border: 1px solid rgba(216, 180, 254, 0.4);
        box-shadow: 0 0 20px rgba(168, 85, 247, 0.5), inset 0 0 10px rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(2px);
        opacity: 0;
      }

      .intro-shatter-active .intro-fragment {
        animation: introShatterOut ${SHATTER_ANIMATION_S}s cubic-bezier(0.23, 1, 0.32, 1) forwards;
      }

      @keyframes introShatterOut {
        0% { opacity: 0; transform: translate(-50%, -50%) translate(0, 0) rotate(0deg) scale(1); }
        15% { opacity: 1; }
        100% { opacity: 0; transform: translate(-50%, -50%) translate(var(--tx), var(--ty)) rotate(var(--rot)) scale(0.3); filter: blur(2px); }
      }

      .intro-frag-1 { width: 80px; height: 4px; clip-path: polygon(0 0, 100% 0, 95% 100%, 5% 100%); }
      .intro-frag-2 { width: 50px; height: 80px; clip-path: polygon(20% 0, 100% 30%, 80% 100%, 0 70%); }
      .intro-frag-3 { width: 100px; height: 30px; clip-path: polygon(0 30%, 30% 0, 100% 50%, 70% 100%); }
      .intro-frag-4 { width: 60px; height: 60px; clip-path: polygon(50% 0, 100% 50%, 50% 100%, 0 50%); }
      .intro-frag-5 { width: 40px; height: 100px; clip-path: polygon(50% 0, 100% 30%, 80% 100%, 20% 100%, 0 30%); }
      .intro-frag-6 { width: 90px; height: 20px; clip-path: polygon(0 0, 100% 30%, 90% 100%, 10% 100%); }
      .intro-frag-7 { width: 70px; height: 70px; clip-path: polygon(30% 0, 70% 0, 100% 50%, 70% 100%, 30% 100%, 0 50%); }
      .intro-frag-8 { width: 35px; height: 90px; clip-path: polygon(0 0, 100% 20%, 70% 100%, 0 80%); }
      .intro-frag-9 { width: 110px; height: 25px; clip-path: polygon(0 50%, 50% 0, 100% 50%, 50% 100%); }
      .intro-frag-10 { width: 55px; height: 55px; clip-path: polygon(0 30%, 50% 0, 100% 30%, 100% 70%, 50% 100%, 0 70%); }
    `,
    [],
  )

  return <style>{css}</style>
}

export default function IntroLoader({ onPhaseChange, onComplete }) {
  const phase = useIntroSequence(onPhaseChange, onComplete)
  const shattering = phase === 'shatter' || phase === 'complete'

  return (
    <motion.div
      className={['pointer-events-none fixed inset-0 z-[100] flex items-center justify-center overflow-hidden bg-black', shattering ? 'intro-shatter-active' : ''].join(' ')}
      initial={{ opacity: 1 }}
      animate={{ opacity: phase === 'complete' ? 0 : 1 }}
      transition={{ duration: OVERLAY_FADE_S, ease: [0.22, 1, 0.36, 1] }}
      aria-label="Mantle AI intro"
    >
      <IntroStyles />
      <div className="relative z-10 flex items-center justify-center">
        <Title />
      </div>
      {shattering && (
        <>
          <LetterFragments />
          <CrystalFragments />
        </>
      )}
    </motion.div>
  )
}
