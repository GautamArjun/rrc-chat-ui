import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // RRC Brand Colors
        'rrc-primary': '#293a44',      // Dark blue-gray (headers, key text)
        'rrc-primary-light': '#3d5060', // Lighter primary for hover
        'rrc-accent': '#0061d4',        // Bright blue (links, buttons)
        'rrc-accent-dark': '#00469a',   // Darker blue (hover states)
        'rrc-muted': '#a1b4bf',         // Light blue-gray (accents)
        'rrc-bg': '#f3f3f3',            // Page background
        // Legacy aliases for compatibility
        'rrc-blue': '#0061d4',
        'rrc-blue-dark': '#00469a',
      },
      fontFamily: {
        sans: ['Open Sans', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        'rrc': '8px',
      },
    },
  },
  plugins: [],
};
export default config;
