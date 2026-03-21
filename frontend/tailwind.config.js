/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        risk: {
          low: '#22c55e',
          medium: '#f59e0b',
          high: '#ef4444',
        },
        surface: {
          900: '#0f1117',
          800: '#1a1d27',
          700: '#252833',
        },
      },
      fontSize: {
        'display': ['4rem', { lineHeight: '1' }],
        'hero': ['2.5rem', { lineHeight: '1.1' }],
      },
      animation: {
        'pulse-slow': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'pulse-fast': 'pulse 0.8s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },
  plugins: [],
}
