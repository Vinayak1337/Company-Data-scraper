"use client";

import { usePathname } from "next/navigation";

const labels: Record<string, string> = {
  "/": "Today",
  "/companies": "Companies",
  "/jobs": "Jobs",
  "/profile": "Profile",
  "/settings": "Settings",
};

export function ShellCrumbs() {
  const pathname = usePathname();
  const label =
    labels[pathname] ??
    labels[
      Object.keys(labels)
        .filter((path) => path !== "/" && pathname.startsWith(path))
        .sort((a, b) => b.length - a.length)[0]
    ] ??
    "Workspace";

  return (
    <div className="font-mono text-[11px] tracking-[0.04em] text-[var(--ink-3)]">
      <span>Workspace</span>
      <span className="mx-1.5 text-[var(--ink-4)]">/</span>
      <span className="text-[var(--ink)]">{label}</span>
    </div>
  );
}
