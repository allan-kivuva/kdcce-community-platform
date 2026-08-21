/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Palette derived from the supplied KDCCE logo.
        kOrange: '#C00059',
        kOrangeDark: '#980044',
        kGreen: '#0068A9',
        kGreen2: '#0A82C8',
        kLime: '#84D318',
        kCream: '#FBFAFD',
        kInk: '#15222B',
        kMuted: '#66747D'
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
