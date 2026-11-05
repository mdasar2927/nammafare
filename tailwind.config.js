/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#fff1f2',
          100: '#ffe4e6',
          200: '#fecdd3',
          300: '#fda4af',
          400: '#fb7185',
          500: '#f43f5e',
          600: '#e11d48',
          700: '#be123c',
          800: '#9f1239',
          900: '#881337',
          950: '#4c0519',
        },
        transit: {
          bus: '#ea580c',        // MTC Red/Orange
          metro: '#0284c7',      // CMRL Blue
          suburban: '#4338ca',   // Southern Railway Navy/Indigo
          auto: '#d97706',       // Chennai Auto Yellow/Amber
          shareauto: '#7c3aed',  // Share Auto Purple
          taxi: '#059669',       // Taxi Emerald
          walk: '#64748b',       // Walking Slate
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      boxShadow: {
        'soft-sm': '0 2px 8px -2px rgba(136, 19, 55, 0.05), 0 1px 4px -1px rgba(0, 0, 0, 0.04)',
        'soft-md': '0 6px 20px -4px rgba(136, 19, 55, 0.08), 0 2px 6px -2px rgba(0, 0, 0, 0.05)',
        'soft-lg': '0 12px 32px -6px rgba(136, 19, 55, 0.12), 0 4px 12px -2px rgba(0, 0, 0, 0.06)',
        'soft-xl': '0 20px 48px -8px rgba(136, 19, 55, 0.15), 0 8px 20px -4px rgba(0, 0, 0, 0.08)',
      }
    },
  },
  plugins: [],
};
