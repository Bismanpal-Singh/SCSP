/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        mantle: {
          bg: '#0a0a0f',
          glass: 'rgba(255, 255, 255, 0.04)',
          border: 'rgba(255, 255, 255, 0.08)',
          purple: '#8b5cf6',
          indigo: '#6366f1',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      backgroundImage: {
        'gradient-purple-indigo': 'linear-gradient(135deg, #8b5cf6 0%, #6366f1 50%, #4f46e5 100%)',
        'text-hero': 'linear-gradient(180deg, #ffffff 0%, #c4b5fd 45%, #8b5cf6 100%)',
      },
      keyframes: {
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'fade-in-up': {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        shake: {
          '0%, 100%': { transform: 'translateX(0)' },
          '20%': { transform: 'translateX(-8px)' },
          '40%': { transform: 'translateX(8px)' },
          '60%': { transform: 'translateX(-5px)' },
          '80%': { transform: 'translateX(5px)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        'glow-pulse': {
          '0%, 100%': { boxShadow: '0 0 20px rgba(139, 92, 246, 0.4), 0 0 40px rgba(99, 102, 241, 0.2)' },
          '50%': { boxShadow: '0 0 32px rgba(139, 92, 246, 0.55), 0 0 56px rgba(99, 102, 241, 0.3)' },
        },
        pipelineBreathe: {
          '0%, 100%': { boxShadow: '0 0 20px rgba(139, 92, 246, 0.35)' },
          '50%': { boxShadow: '0 0 36px rgba(139, 92, 246, 0.55)' },
        },
      },
      animation: {
        'fade-in': 'fade-in 0.55s cubic-bezier(0.33, 0.9, 0.2, 1) forwards',
        'fade-in-up': 'fade-in-up 0.7s ease-out forwards',
        'fade-in-up-delay': 'fade-in-up 0.7s ease-out 0.12s forwards',
        'fade-in-up-delay-2': 'fade-in-up 0.7s ease-out 0.24s forwards',
        'fade-in-up-delay-3': 'fade-in-up 0.7s ease-out 0.36s forwards',
        shake: 'shake 0.45s ease-in-out',
        shimmer: 'shimmer 1.2s ease-in-out infinite',
        'glow-pulse': 'glow-pulse 1.5s ease-in-out infinite',
        'pipeline-breathe': 'pipelineBreathe 2.4s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}
