/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        crt: {
          green: '#00ff00',
          'green-dim': '#00aa00',
          'green-dark': '#005500',
          amber: '#ffaa00',
          'amber-dim': '#cc8800',
          red: '#ff0000',
          'red-dim': '#cc0000',
          black: '#0a0a0a',
          dark: '#111111',
          panel: '#1a1a1a',
          'panel-light': '#222222',
          border: '#333333',
        },
        risk: {
          low: '#00ff00',
          medium: '#ffaa00',
          high: '#ff0000',
        },
        surface: {
          900: '#0a0a0a',
          800: '#111111',
          700: '#1a1a1a',
        },
      },
      fontFamily: {
        mono: ['VT323', 'monospace'],
        pixel: ['"Press Start 2P"', 'monospace'],
      },
      fontSize: {
        'display': ['4rem', { lineHeight: '1' }],
        'hero': ['2.5rem', { lineHeight: '1.1' }],
      },
      animation: {
        'pulse-slow': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'pulse-fast': 'pulse 0.8s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'blink': 'blink 1s step-end infinite',
        'scanline': 'scanline 8s linear infinite',
        'glow-pulse': 'glow-pulse 2s ease-in-out infinite',
      },
      keyframes: {
        blink: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0' },
        },
        scanline: {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100vh)' },
        },
        'glow-pulse': {
          '0%, 100%': { boxShadow: '0 0 5px currentColor, 0 0 10px currentColor' },
          '50%': { boxShadow: '0 0 20px currentColor, 0 0 40px currentColor' },
        },
      },
    },
  },
  plugins: [],
}
