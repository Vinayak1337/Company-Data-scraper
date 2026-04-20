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
        success: "#22C55E"
      },
      boxShadow: {
        glow: "0 0 40px rgba(99,102,241,0.16)"
      }
    }
  },
  plugins: []
};
