/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        jarvis: {
          bg:     '#030712',
          panel:  'rgba(6,15,30,0.7)',
          cyan:   '#00f2ff',
          purple: '#7c3aed',
          blue:   '#3b82f6',
          green:  '#22c55e',
          yellow: '#eab308',
          red:    '#ef4444',
          border: 'rgba(0,242,255,0.15)',
        }
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', '"Fira Mono"', 'monospace'],
        hud:  ['"Rajdhani"', '"Orbitron"', 'sans-serif'],
      },
      boxShadow: {
        'glow-cyan':   '0 0 25px rgba(0,242,255,0.35)',
        'glow-purple': '0 0 25px rgba(124,58,237,0.45)',
        'glow-sm':     '0 0 8px  rgba(0,242,255,0.2)',
      },
      animation: {
        'pulse-slow':  'pulse 3s ease-in-out infinite',
        'spin-slow':   'spin 20s linear infinite',
        'flicker':     'flicker 4s infinite',
        'data-stream': 'data-stream 20s linear infinite',
      },
      keyframes: {
        flicker: {
          '0%,100%': { opacity: '1' },
          '50%':     { opacity: '0.6' },
        },
        'data-stream': {
          '0%':   { transform: 'translateY(0)' },
          '100%': { transform: 'translateY(-50%)' },
        },
      },
    },
  },
  plugins: [],
}
