import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        bg: '#fdf6ec',
        card: '#fff8f0',
        dark: '#2d1b0e',
        accent: { DEFAULT: '#c4622a', light: '#e8845a' },
        muted: '#e8d5bc',
        green: { DEFAULT: '#4a7c4e', light: '#6aab6e' },
        blue: '#8b9dc3',
        gold: '#b8860b',
        warm: { mid: '#7a5c42', light: '#c4a882' },
      },
      fontFamily: {
        serif: ['var(--font-serif)', 'Georgia', 'serif'],
        sans: ['var(--font-sans)', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        card: '0 2px 8px rgba(45, 27, 14, 0.05)',
        'card-hover': '0 6px 24px rgba(45, 27, 14, 0.12)',
      },
      transitionDuration: { DEFAULT: '150ms' },
    },
  },
  plugins: [],
}

export default config
