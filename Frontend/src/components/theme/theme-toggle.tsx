"use client";

import { Monitor, Moon, Sun } from "lucide-react";
import { cn } from "@/lib/utils";
import { useTheme } from "./theme-provider";

export function ThemeToggle({ className }: { className?: string }) {
  const { theme, setTheme } = useTheme();

  function toggleTheme() {
    const nextTheme = theme === "dark" ? "light" : "dark";
    setTheme(nextTheme);
    document.documentElement.dataset.theme = nextTheme;
  }

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className={cn(
        "inline-grid h-[30px] w-[30px] place-items-center rounded-[3px] text-[var(--ink-3)] transition hover:bg-[var(--bg-hover)] hover:text-[var(--ink)]",
        className,
      )}
      aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
      title={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
    >
      {theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}
      <Monitor className="sr-only" size={15} />
    </button>
  );
}
