import React from 'react'
import Hero from '../components/Hero'
import InteractiveInput from '../components/InteractiveInput'

export default function HomePage({ useMock = false }) {
  return (
    <Hero>
      <InteractiveInput useMock={useMock} />
    </Hero>
  )
}
