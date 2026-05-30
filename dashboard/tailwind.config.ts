import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        danger: "#ef4444",
        warning: "#f59e0b",
        safe: "#22c55e",
      },
    },
  },
  plugins: [],
};
export default config;
