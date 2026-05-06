/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      backgroundImage: {
        'gradient-brand':   'linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #a855f7 100%)',
        'gradient-brand-h': 'linear-gradient(90deg, #6366f1, #8b5cf6, #a855f7)',
        'gradient-card':    'linear-gradient(135deg, rgba(99,102,241,0.07) 0%, rgba(168,85,247,0.03) 100%)',
      },
      boxShadow: {
        'glow-sm':    '0 0 12px rgba(99,102,241,0.20)',
        'glow':       '0 0 28px rgba(99,102,241,0.30)',
        'card':       '0 1px 3px rgba(0,0,0,0.4), 0 0 0 1px rgba(99,102,241,0.08)',
        'card-hover': '0 4px 24px rgba(0,0,0,0.5), 0 0 0 1px rgba(99,102,241,0.22)',
      },
      animation: {
        'fade-in':  'fadeIn 0.25s ease-out',
        'slide-up': 'slideUp 0.25s ease-out',
      },
      keyframes: {
        fadeIn:  { from: { opacity: '0' }, to: { opacity: '1' } },
        slideUp: { from: { opacity: '0', transform: 'translateY(6px)' }, to: { opacity: '1', transform: 'translateY(0)' } },
      },
    },
  },
  plugins: [],
}
