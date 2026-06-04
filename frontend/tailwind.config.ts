import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0b1220",
        panel: "#111b2e",
        panel2: "#16233a",
        line: "#223252",
        accent: "#7dd3fc",
        accent2: "#f59e0b",
      },
      boxShadow: {
        soft: "0 20px 60px rgba(0, 0, 0, 0.25)",
      },
    },
  },
  plugins: [],
};

export default config;
