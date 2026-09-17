/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: ['class', '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        surface: 'var(--od-surface)',
        'surface-raised': 'var(--od-surface-raised)',
        ink: 'var(--od-ink)',
        'ink-muted': 'var(--od-ink-muted)',
        line: 'var(--od-line)',
        accent: 'var(--od-accent)',
        'accent-ink': 'var(--od-accent-ink)',
        positive: 'var(--od-positive)',
        warning: 'var(--od-warning)',
        danger: 'var(--od-danger)',
      },
      borderRadius: { card: '14px' },
      spacing: { 'safe-bottom': 'calc(env(safe-area-inset-bottom) + 4.5rem)' },
      minHeight: { touch: '44px' },
      minWidth: { touch: '44px' },
    },
  },
  plugins: [],
};
