/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#0b0d10",
          900: "#12151b",
          800: "#1a1f28",
          700: "#242a36",
          600: "#3a4354",
          500: "#5c677a",
          400: "#8b96a8",
          300: "#b4bdcc",
          200: "#d6dbe5",
          100: "#eef1f6",
        },
        mist: "#f4f5f7",
        line: "#e6e8ee",
        /** Slightly cooler / warmer neutrals for borders (whisper-level only). */
        lineSubtle: "#e7e9ef",
        lineWarm: "#e9e7e3",
        /**
         * Pastel-adjacent surfaces: still reads monochrome at a glance; warmth shows up in rhythm.
         * Use for bands, cards, and modules — not loud accents.
         */
        surface: {
          /** Flat base behind marketing content — bands/cards sit visibly above this */
          page: "#f4f5f7",
          "band-warm": "#ebe6df",
          "band-cool": "#e3e9f2",
          "band-sage": "#e4ebe5",
          "band-blush": "#ebe4e3",
          card: "#f9fafb",
          "card-warm": "#f3f0ea",
          "card-cool": "#ebeef4",
        },
      },
      fontFamily: {
        sans: ["var(--font-geist-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["var(--font-geist-mono)", "ui-monospace", "monospace"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(15, 23, 42, 0.06), 0 8px 24px rgba(15, 23, 42, 0.06)",
      },
    },
  },
  plugins: [],
};
