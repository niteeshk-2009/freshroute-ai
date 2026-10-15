/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        forest: {
          50: '#F0FDF4',
          100: '#DCFCE7',
          200: '#BBF7D0',
          300: '#86EFAC',
          400: '#4ADE80',
          500: '#22C55E',
          600: '#16A34A',
          700: '#15803D',
          800: '#166534',
          900: '#14532D',
          950: '#052E16',
        },
        fresh: {
          lime: '#84CC16',
          limeDark: '#4D7C0F',
          amber: '#F59E0B',
          red: '#EF4444',
          charcoal: '#1F2937',
          warmWhite: '#FAFAF9',
          cardBg: '#FFFFFF',
        }
      }
    },
  },
  plugins: [],
}
