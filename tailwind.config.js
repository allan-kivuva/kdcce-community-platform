/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Palette derived from the supplied KDCCE logo. Solid brand fills
        // (buttons, colored panels) stay constant across themes since they
        // always pair with white text/icons. Text/surface tokens below are
        // CSS-variable-driven so they adapt between light and dark.
        kOrange: '#C00059',
        kOrangeDark: '#980044',
        kGreen: '#0068A9',
        kGreen2: '#0A82C8',
        kLime: '#84D318',
        kCream: 'rgb(var(--k-surface-2) / <alpha-value>)',
        kInk: 'rgb(var(--k-ink) / <alpha-value>)',
        kMuted: 'rgb(var(--k-muted) / <alpha-value>)',
        kBg: 'rgb(var(--k-bg) / <alpha-value>)',
        kSurface: 'rgb(var(--k-surface) / <alpha-value>)',
        kTint: 'rgb(var(--k-tint) / <alpha-value>)',
        kBorder: 'rgb(var(--k-border) / <alpha-value>)',
        kBorderSoft: 'rgb(var(--k-border-soft) / <alpha-value>)'
      },
      boxShadow: {
        soft: '0 8px 30px rgba(0,104,169,.09)'
      },
      fontFamily: {
        display: ['Poppins', 'sans-serif'],
        body: ['Inter', 'sans-serif']
      }
    }
  },
  plugins: []
}
