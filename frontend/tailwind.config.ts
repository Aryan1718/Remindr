import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: "var(--color-surface)",
        "surface-alt": "var(--color-surface-alt)",
        "surface-elevated": "var(--color-surface-elevated)",
        ink: "var(--color-ink)",
        muted: "var(--color-muted)",
        faint: "var(--color-faint)",
        border: "var(--color-border)",
        accent: "var(--color-accent)",
        "accent-strong": "var(--color-accent-strong)",
        focus: "var(--color-focus)",
        link: "var(--color-link)",
        success: "var(--color-success)",
        warning: "var(--color-warning)",
        danger: "var(--color-danger)",
      },
      boxShadow: {
        card: "var(--shadow-card)",
        deep: "var(--shadow-deep)",
      },
      borderRadius: {
        card: "0px",
        panel: "0px",
      },
      fontFamily: {
        sans: ['"Arial Narrow"', "Arial", "Helvetica", "sans-serif"],
        display: ['"Arial Narrow"', "Arial", "Helvetica", "sans-serif"],
      },
      backgroundImage: {
        "hero-sheen":
          "linear-gradient(120deg, rgba(255, 255, 255, 0.06) 0%, rgba(255, 255, 255, 0) 35%), linear-gradient(180deg, rgba(0, 0, 0, 0) 0%, rgba(0, 0, 0, 0.72) 100%)",
      },
    },
  },
  plugins: [],
};

export default config;
