import type { ReactNode } from "react";
import Link from "next/link";
import { Bell, RefreshCw } from "lucide-react";
import { CommandPalette } from "@/components/ui/command-palette";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { NavLink } from "./nav-link";
import { ShellCrumbs } from "./shell-crumbs";

const primaryNav = [
  { href: "/", label: "Today", shortcut: "T", icon: "today" },
  { href: "/companies", label: "Companies", shortcut: "C", icon: "companies" },
  { href: "/jobs", label: "Jobs", shortcut: "J", icon: "jobs" },
  { href: "/applications", label: "Applications", shortcut: "A", icon: "applications" },
  { href: "/agents", label: "Agents", shortcut: "G", icon: "agents" },
  { href: "/analytics", label: "Analytics", shortcut: "N", icon: "analytics" },
] as const;

const secondaryNav = [
  { href: "/profile", label: "Profile", icon: "profile" },
  { href: "/settings", label: "Settings", icon: "settings" },
] as const;

type AppShellProps = {
  children: ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="min-h-screen text-[var(--ink)] lg:flex">
      <aside className="hidden w-[232px] shrink-0 border-r border-[var(--line)] bg-[var(--bg)] px-4 py-6 lg:fixed lg:inset-y-0 lg:left-0 lg:flex lg:flex-col">
        <div className="px-2 pb-8">
          <Link href="/" className="flex items-center gap-3">
            <div className="relative grid h-[22px] w-[22px] place-items-center rounded border-[1.5px] border-[var(--ink)]">
              <span className="h-1.5 w-1.5 rounded-full bg-[var(--accent)]" />
            </div>
            <div className="min-w-0">
              <div className="truncate font-serif text-[17px] font-medium tracking-[-0.01em]">
                Job Scout
              </div>
              <div className="font-mono text-[10px] text-[var(--ink-3)]">
                v2 · operator
              </div>
            </div>
          </Link>
        </div>

        <nav aria-label="Primary" className="px-2">
          <div className="mb-2 px-2 font-mono text-[10px] uppercase tracking-[0.1em] text-[var(--ink-4)]">
            Workflow
          </div>
          <div className="flex flex-col gap-0.5">
            {primaryNav.map((item) => (
              <NavLink key={item.href} {...item} />
            ))}
          </div>
        </nav>

        <nav aria-label="Workspace" className="mt-4 px-2">
          <div className="mb-2 px-2 font-mono text-[10px] uppercase tracking-[0.1em] text-[var(--ink-4)]">
            Workspace
          </div>
          <div className="flex flex-col gap-0.5">
            {secondaryNav.map((item) => (
              <NavLink key={item.href} {...item} />
            ))}
          </div>
        </nav>

        <div className="mt-auto border-t border-[var(--line)] px-2 pt-3">
          <div className="flex items-center gap-2 rounded-[3px] border border-[var(--line)] bg-[var(--bg-raised)] px-3 py-2 text-xs text-[var(--ink-2)]">
            <span className="h-1.5 w-1.5 rounded-full bg-[var(--ok)]" />
            <span>Backend</span>
            <span className="ml-auto font-mono text-[11px] text-[var(--ink-3)]">84ms</span>
          </div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col lg:pl-[232px]">
        <header className="overflow-hidden border-b border-[var(--line)] bg-[var(--bg)] lg:hidden">
          <div className="flex items-center justify-between gap-3 px-4 py-3">
            <Link href="/" className="min-w-0">
              <div className="truncate font-serif text-base font-medium">Job Scout</div>
              <div className="font-mono text-[10px] text-[var(--ink-3)]">
                v2 · operator
              </div>
            </Link>
            <div className="flex items-center gap-2">
              <CommandPalette />
              <ThemeToggle />
            </div>
          </div>
          <nav aria-label="Mobile" className="grid w-full max-w-full grid-cols-2 gap-1 px-3 pb-3 sm:grid-cols-4">
            {[...primaryNav, ...secondaryNav].map((item) => (
              <div key={item.href} className="min-w-0">
                <NavLink {...item} shortcut={undefined} />
              </div>
            ))}
          </nav>
        </header>

        <header className="sticky top-0 z-40 hidden h-[58px] items-center gap-3 border-b border-[var(--line)] bg-[color-mix(in_srgb,var(--bg)_94%,transparent)] px-8 backdrop-blur lg:flex">
          <ShellCrumbs />
          <div className="flex-1" />

          <div className="flex items-center gap-2">
            <CommandPalette />
            <ThemeToggle />
            <button
              type="button"
              className="inline-grid h-[30px] w-[30px] place-items-center rounded-[3px] text-[var(--ink-3)] transition hover:bg-[var(--bg-hover)] hover:text-[var(--ink)]"
              aria-label="Notifications"
              title="Notifications"
            >
              <Bell size={15} />
            </button>
            <button
              type="button"
              className="inline-grid h-[30px] w-[30px] place-items-center rounded-[3px] text-[var(--ink-3)] transition hover:bg-[var(--bg-hover)] hover:text-[var(--ink)]"
              aria-label="Run scans"
              title="Run scans"
            >
              <RefreshCw size={15} />
            </button>
          </div>
        </header>

        <main className="min-w-0 flex-1 console-grid-bg">
          <div className="mx-auto w-full max-w-[1320px] px-5 py-8 sm:px-8 lg:px-12 lg:py-12">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
