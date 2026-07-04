import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#17201b",
        moss: "#2f5d50",
        mint: "#cce7d8",
        amberline: "#d99a2b",
        paper: "#f7f5ef"
      }
    }
  },
  plugins: []
};

export default config;
