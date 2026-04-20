module.exports = {
  content: [
    "./templates/**/*.html",
    "./companies/templates/**/*.html",
    "./dashboard/templates/**/*.html",
    "./jobs/templates/**/*.html"
  ],
  theme: {
    extend: {
      colors: {
        ink: "#0B0F19",
        panel: "#111827",
        line: "#1F2937",
        brand: "#6366F1",
        success: "#22C55E",
        cream: "#FAF7F0",
        paper: "#FFFFFF",
        gold: "#C9972B",
        goldDark: "#A97916",
        goldSoft: "#FFF4D6",
        charcoal: "#1F2933",
        muted: "#6B7280",
        warmLine: "#E7DEC8"
      },
      boxShadow: {
        glow: "0 0 40px rgba(99,102,241,0.16)",
        soft: "0 18px 42px rgba(31,41,51,0.08)"
      }
    }
  },
  plugins: []
};
