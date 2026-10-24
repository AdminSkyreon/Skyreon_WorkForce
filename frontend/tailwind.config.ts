import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#081020",
        forest: "#0060a8",
        copper: "#00a3dc",
        paper: "#f4f8fc",
        mist: "#e8f1f8",
      },
      fontFamily: {
        sans: ["var(--font-manrope)", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["var(--font-fraunces)", "ui-serif", "Georgia", "serif"],
      },
      boxShadow: {
        card: "0 12px 40px -24px rgba(8, 16, 32, 0.35)",
      },
    },
  },
  plugins: [],
};

export default config;
