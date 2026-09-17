import type { Config } from "tailwindcss";

export default {
  content: ["./app/**/*.{ts,tsx}", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#17202a",
        paper: "#f7f8f5",
        signal: "#0f766e",
        caution: "#b45309",
        line: "#d8ddd4"
      }
    }
  },
  plugins: []
} satisfies Config;
