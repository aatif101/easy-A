import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#18231f",
        paper: "#f4f1e8",
        spruce: "#064c3b",
        moss: "#dce8dc",
        brass: "#b7791f",
        rule: "#d8d4c8",
      },
      fontFamily: {
        display: ["Charter", "Bitstream Charter", "Cambria", "serif"],
        sans: ["Aptos", "Segoe UI", "sans-serif"],
        mono: ["IBM Plex Mono", "Cascadia Mono", "monospace"],
      },
      boxShadow: {
        ledger: "0 18px 45px -32px rgba(24, 35, 31, 0.6)",
      },
    },
  },
  plugins: [],
} satisfies Config;
