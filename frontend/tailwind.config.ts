import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // SingleStore brand purple, led by the deep primary. Reserved for all
        // Aura / "Powered by" chrome — never recolored to a Meridian hue.
        s2: {
          purple: "#553BCC",
          purpleLight: "#6E56CF",
          purpleDark: "#3B278F",
          ink: "#1B1435",
        },
        // Meridian Mutual Insurance brand — trustworthy carrier navy/blue with
        // teal (positive/healthy), amber (warning/at-risk), and red (critical).
        meridian: {
          navy: "#0A2540",
          blue: "#1E5EFF",
          teal: "#0FB5AE",
          amber: "#F5A623",
          red: "#E5484D",
        },
        // Legacy alias: chat bubbles reference `rev.*`. Repointed to Meridian
        // hexes so any un-migrated className still renders on-brand.
        rev: {
          teal: "#1E5EFF",
          green: "#0FB5AE",
        },
        // Legacy alias from the enova skeleton. Repointed to Meridian hexes
        // (navy→navy, blue/bright→brand blue, green→teal) so any un-migrated
        // `enova-*` className still renders on-brand.
        enova: {
          blue: "#1E5EFF",
          navy: "#0A2540",
          green: "#0FB5AE",
          bright: "#1E5EFF",
          ink: "#0A2540",
        },
        // Legacy alias: any un-migrated `bm.*` className still renders on-brand
        // by pointing at the Meridian hexes.
        bm: {
          navy: "#0A2540",
          blue: "#1E5EFF",
          bright: "#1E5EFF",
          ink: "#0A2540",
        },
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "system-ui",
          "sans-serif",
        ],
        mono: [
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Monaco",
          "Consolas",
          "monospace",
        ],
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      keyframes: {
        "pulse-soft": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.5" },
        },
        "fade-in": {
          from: { opacity: "0", transform: "translateY(4px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "pulse-soft": "pulse-soft 2s ease-in-out infinite",
        "fade-in": "fade-in 0.25s ease-out",
      },
    },
  },
  plugins: [],
};

export default config;
