import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          red: "#E50914",
          bg: "#07070A"
        }
      },
      boxShadow: {
        glow: "0 0 30px rgba(229,9,20,0.35)"
      }
    }
  },
  plugins: []
};

export default config;
