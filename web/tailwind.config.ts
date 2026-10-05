import type { Config } from "tailwindcss";

// Colors come from the USF brand palette (usf.edu/ucm/marketing/colors.aspx).
// Green is reserved for the A share and the one primary action per view.
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#303434",
        slate: "#466069",
        green: { DEFAULT: "#006747", deep: "#005432" },
        silver: "#CAD2D8",
        line: "#E3E6E8",
        wash: "#F6F7F8",
        warn: "#7A4E10",
      },
      fontFamily: {
        sans: ['"Public Sans"', "system-ui", "sans-serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
} satisfies Config;
