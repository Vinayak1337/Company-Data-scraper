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
        danger: "#DC2626",
        warning: "#F59E0B",
        cream: "#FAF7F0",
        paper: "#FFFFFF",
        gold: "#D4AF37",
        goldDark: "#996515",
        goldSoft: "#FDE68A",
        charcoal: "#1F2933",
        muted: "#6B7280",
        warmLine: "#E7DEC8"
      },
      boxShadow: {
        glow: "0 0 20px rgba(212,175,55,0.45), 0 0 48px rgba(212,175,55,0.18)",
        soft: "0 18px 42px rgba(212,175,55,0.10)",
        innerGlow: "inset 0 1px 1px rgba(253,230,138,0.7), 0 2px 4px rgba(212,175,55,0.15)",
        "elev-1": "0 1px 3px rgba(212,175,55,0.10), 0 4px 12px rgba(212,175,55,0.07)",
        "elev-2": "0 4px 16px rgba(212,175,55,0.18), 0 10px 28px rgba(212,175,55,0.10)",
        "elev-3": "0 8px 40px rgba(212,175,55,0.24), 0 24px 64px rgba(212,175,55,0.14)"
      },
      backgroundImage: {
        'gold-metallic': "linear-gradient(110deg, #D4AF37 35%, #E7C678 50%, #D4AF37 65%)",
        'hero-radial': "radial-gradient(1200px 400px at 50% -10%, rgba(212,175,55,0.18), transparent 60%)",
        'card-sheen': "linear-gradient(135deg, rgba(255,255,255,0.65) 0%, rgba(250,247,240,0.3) 100%)"
      },
      backgroundSize: {
        '200%': '200% 100%',
      },
      keyframes: {
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        'fade-in-up': {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'pulse-soft': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.55' },
        },
        'spin-slow': {
          '0%': { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        },
        'toast-in': {
          '0%': { opacity: '0', transform: 'translateY(-12px) scale(0.96)' },
          '100%': { opacity: '1', transform: 'translateY(0) scale(1)' },
        },
      },
      animation: {
        shimmer: 'shimmer 8s infinite linear',
        'fade-in-up': 'fade-in-up 0.45s cubic-bezier(0.22,0.61,0.36,1) both',
        'fade-in': 'fade-in 0.3s ease-out both',
        'pulse-soft': 'pulse-soft 2.4s ease-in-out infinite',
        'spin-slow': 'spin-slow 1s linear infinite',
        'toast-in': 'toast-in 0.25s cubic-bezier(0.22,0.61,0.36,1) both',
      }
    }
  },
  plugins: []
};
