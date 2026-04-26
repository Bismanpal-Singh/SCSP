import React from 'react'

export default function Hero({ children }) {
  return (
    <section
      className="relative z-10 flex min-h-[calc(100vh-3.5rem)] flex-col items-center justify-center px-4 pb-16 pt-8 sm:min-h-[calc(100vh-4rem)] sm:px-6 sm:pb-20 sm:pt-12 lg:px-8"
      aria-labelledby="hero-title"
    >
      <div className="mx-auto flex w-full max-w-[1600px] flex-col items-center text-center">
        <h1
          id="hero-title"
          className="bg-gradient-to-b from-white via-violet-100 to-violet-400/90 bg-clip-text text-4xl font-bold tracking-tight text-transparent sm:text-5xl md:text-6xl lg:text-7xl"
          style={{ textShadow: '0 0 80px rgba(139, 92, 246, 0.25)' }}
        >
          Mantle AI
        </h1>
        <p className="mt-6 max-w-2xl text-base leading-relaxed text-white/75 sm:text-lg md:mt-8">
          An AI agent that autonomously discovers and optimizes mineral compositions through iterative simulation.
        </p>
        <div className="mt-10 w-full md:mt-12">
          {children}
        </div>
      </div>
    </section>
  )
}
