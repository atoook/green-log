/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,ts}'],
  theme: {
    extend: {
      colors: {
        leaf: {
          50: '#f4fbf6',
          100: '#e5f5e9',
          600: '#2f7d4d',
          700: '#24623c',
        },
        soil: {
          50: '#fbf7f0',
          100: '#f2e6d4',
          700: '#6e4e2e',
        },
      },
    },
  },
  plugins: [],
}
