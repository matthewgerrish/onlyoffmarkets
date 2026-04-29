const path = require('node:path');

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    path.resolve(__dirname, 'index.html'),
    path.resolve(__dirname, 'src/**/*.{ts,tsx}'),
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#e8f1ff',
          100: '#cfe1ff',
          200: '#9cc2ff',
          300: '#5fa0ff',
          400: '#2c83ff',
          500: '#1d6cf2',
          600: '#0a6bd6',
          700: '#0856ad',
          800: '#0a4a8c',
          900: '#0f3a6e',
          navy: '#0f1f3d',
        },
        signal: {
          hot: '#ff3b5c',
          warm: '#ff8a3d',
          warming: '#ffc83d',
          cold: '#00AFF0',
          top: '#ff2d7c',
        },
      },
      fontFamily: {
        display: ['Poppins', 'system-ui', 'sans-serif'],
        sans: ['Poppins', 'Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        brand:    '0 8px 24px -8px rgba(29, 108, 242, 0.35)',
        'brand-lg': '0 24px 48px -16px rgba(29, 108, 242, 0.35)',
        'glow-rose':   '0 0 0 4px rgba(244, 63, 94, 0.18)',
        'glow-brand':  '0 0 0 4px rgba(29, 108, 242, 0.18)',
      },
      keyframes: {
        'fade-in':       { '0%': { opacity: '0' },                         '100%': { opacity: '1' } },
        'fade-in-up':    { '0%': { opacity: '0', transform: 'translateY(12px)' },  '100%': { opacity: '1', transform: 'translateY(0)' } },
        'fade-in-down':  { '0%': { opacity: '0', transform: 'translateY(-8px)' },  '100%': { opacity: '1', transform: 'translateY(0)' } },
        'pop-in':        { '0%': { opacity: '0', transform: 'scale(.92)' },         '100%': { opacity: '1', transform: 'scale(1)' } },
        'slide-up':      { '0%': { transform: 'translateY(8px)', opacity: '0' },    '100%': { transform: 'translateY(0)', opacity: '1' } },
        'slide-in-right':{ '0%': { transform: 'translateX(100%)' },                  '100%': { transform: 'translateX(0)' } },
        'shimmer':       { '0%': { backgroundPosition: '-200px 0' },                 '100%': { backgroundPosition: '200px 0' } },
        'pin-drop':      { '0%': { opacity: '0', transform: 'translateY(-12px) scale(.7)' }, '60%': { opacity: '1', transform: 'translateY(2px) scale(1.1)' }, '100%': { transform: 'translateY(0) scale(1)' } },
        'pulse-ring':    { '0%': { transform: 'scale(.85)', opacity: '0.6' },        '100%': { transform: 'scale(1.6)', opacity: '0' } },
      },
      animation: {
        'fade-in':       'fade-in 200ms ease-out both',
        'fade-in-up':    'fade-in-up 350ms cubic-bezier(0.16, 1, 0.3, 1) both',
        'fade-in-down':  'fade-in-down 220ms ease-out both',
        'pop-in':        'pop-in 240ms cubic-bezier(0.16, 1, 0.3, 1) both',
        'slide-up':      'slide-up 240ms cubic-bezier(0.16, 1, 0.3, 1) both',
        'slide-in-right':'slide-in-right 260ms cubic-bezier(0.16, 1, 0.3, 1)',
        'shimmer':       'shimmer 1.6s linear infinite',
        'pin-drop':      'pin-drop 360ms cubic-bezier(0.34, 1.56, 0.64, 1) both',
        'pulse-ring':    'pulse-ring 1.6s ease-out infinite',
      },
    },
  },
  plugins: [],
};
