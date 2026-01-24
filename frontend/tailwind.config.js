/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Primary colors using CSS variables for theme support
        primary: {
          DEFAULT: 'var(--color-primary)',
          hover: 'var(--color-primary-hover)',
          active: 'var(--color-primary-active)',
        },
        // Text colors
        text: {
          primary: 'var(--color-text-primary)',
          secondary: 'var(--color-text-secondary)',
          tertiary: 'var(--color-text-tertiary)',
          placeholder: 'var(--color-text-placeholder)',
          disabled: 'var(--color-text-disabled)',
          inverse: 'var(--color-text-inverse)',
        },
        // Background colors
        bg: {
          primary: 'var(--color-bg-primary)',
          secondary: 'var(--color-bg-secondary)',
          tertiary: 'var(--color-bg-tertiary)',
          hover: 'var(--color-bg-hover)',
          active: 'var(--color-bg-active)',
          disabled: 'var(--color-bg-disabled)',
        },
        // Border colors
        border: {
          light: 'var(--color-border-light)',
          medium: 'var(--color-border-medium)',
          dark: 'var(--color-border-dark)',
          focus: 'var(--color-border-focus)',
        },
        // Semantic colors
        success: 'var(--color-success)',
        error: 'var(--color-error)',
        warning: 'var(--color-warning)',
        info: 'var(--color-info)',
        // Notebook-specific colors
        notebook: {
          bg: 'var(--notebook-bg)',
          text: 'var(--notebook-text)',
          accent: 'var(--notebook-accent)',
          // Page colors
          'page-white': 'var(--page-white)',
          'page-cream': 'var(--page-cream)',
          'page-manila': 'var(--page-manila)',
          'page-blueprint': 'var(--page-blueprint)',
          // Pen colors
          'pen-black': 'var(--pen-black)',
          'pen-gray': 'var(--pen-gray)',
          'pen-blue': 'var(--pen-blue)',
          'pen-red': 'var(--pen-red)',
          'pen-green': 'var(--pen-green)',
          'pen-purple': 'var(--pen-purple)',
        },
      },
      fontFamily: {
        'sans': 'var(--font-sans)',
        'serif': 'var(--font-serif)',
        'mono': 'var(--font-mono)',
        'notebook': ['Georgia', 'Palatino', 'Times New Roman', 'serif'],
        'handwriting': ['Caveat', 'cursive'],
      },
      fontSize: {
        'xs': 'var(--text-xs)',
        'sm': 'var(--text-sm)',
        'base': 'var(--text-base)',
        'lg': 'var(--text-lg)',
        'xl': 'var(--text-xl)',
        '2xl': 'var(--text-2xl)',
        '3xl': 'var(--text-3xl)',
        '4xl': 'var(--text-4xl)',
      },
      boxShadow: {
        'sm': 'var(--shadow-sm)',
        'md': 'var(--shadow-md)',
        'lg': 'var(--shadow-lg)',
        'xl': 'var(--shadow-xl)',
      },
      borderRadius: {
        'sm': 'var(--radius-sm)',
        'md': 'var(--radius-md)',
        'lg': 'var(--radius-lg)',
        'xl': 'var(--radius-xl)',
        'full': 'var(--radius-full)',
      },
    },
  },
  plugins: [],
}
