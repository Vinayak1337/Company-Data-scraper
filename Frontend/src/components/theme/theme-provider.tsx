"use client";

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

type Theme = "dark" | "light";

const storageKey = "job-scout-theme";
const ThemeContext = createContext<{
  theme: Theme;
  setTheme: (theme: Theme) => void;
} | null>(null);

function getInitialTheme(): Theme {
  if (typeof window === "undefined") return "light";
  const stored = window.localStorage.getItem(storageKey);
  if (stored === "light" || stored === "dark") return stored;
  return "light";
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>("light");
  const hydratedRef = useRef(false);

  useEffect(() => {
    const initialTheme = getInitialTheme();
    document.documentElement.dataset.theme = initialTheme;

    const frame = window.requestAnimationFrame(() => {
      hydratedRef.current = true;
      setTheme(initialTheme);
    });

    return () => window.cancelAnimationFrame(frame);
  }, []);

  useEffect(() => {
    if (!hydratedRef.current) return;
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem(storageKey, theme);
  }, [theme]);

  useEffect(() => {
    window.__setJobScoutTheme = setTheme;
    return () => {
      delete window.__setJobScoutTheme;
    };
  }, []);

  const value = useMemo(() => ({ theme, setTheme }), [theme]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within ThemeProvider");
  }
  return context;
}

declare global {
  interface Window {
    __setJobScoutTheme?: (theme: Theme) => void;
  }
}
