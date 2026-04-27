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
        brand: '0 8px 24px -8px rgba(0, 175, 240, 0.45)',
      },
    },
  },
  plugins: [],
};
