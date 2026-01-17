/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#667eea',
          hover: '#5a67d8',
        },
        notebook: {
          // Page colors
          'page-white': '#ffffff',
          'page-cream': '#fef9f3',
          'page-manila': '#f4e8d0',
          'page-blueprint': '#1e3a5f',
          // Pen colors
          'pen-black': '#1a1a1a',
          'pen-gray': '#4a5568',
          'pen-blue': '#2563eb',
          'pen-red': '#dc2626',
          'pen-green': '#16a34a',
          'pen-purple': '#9333ea',
        },
      },
      fontFamily: {
        'notebook': ['Georgia', 'Palatino', 'Times New Roman', 'serif'],
        'handwriting': ['Caveat', 'cursive'],
      },
    },
  },
  plugins: [],
}
