import type { Config } from "tailwindcss";

export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Editorial neutrals with a single accent. Ink is near-black with a
        // blue cast so long-form text reads warm rather than harsh.
        ink: "#16202c",
        accent: "#a4321f",
        paper: "#faf9f7",
        rule: "#e2ded8",
        muted: "#6b7280",
      },
      fontFamily: {
        serif: ["var(--font-serif)", "Georgia", "serif"],
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      maxWidth: {
        // ~68 characters at the report's body size: the readable measure.
        measure: "44rem",
      },
    },
  },
  plugins: [],
} satisfies Config;
