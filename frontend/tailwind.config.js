/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#F3EEE3",
        panel: "#FBF9F3",
        ink: "#17140F",
        line: "#D9D2C2",
        muted: "#8C8676",
        node: {
          grey: "#B7B0A0",
          blue: "#3452D9",
          orange: "#DD6B2C",
        },
        thread: {
          red: "#9A3B34",
          grey: "#C9C2B1",
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "sans-serif",
        ],
        mono: ["IBM Plex Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      fontSize: {
        micro: ["0.625rem", { lineHeight: "0.85rem", letterSpacing: "0.06em" }],
      },
    },
  },
  plugins: [],
};
