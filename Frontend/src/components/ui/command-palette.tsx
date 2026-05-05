"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  Building2,
  ListChecks,
  Mail,
  Search,
  Settings,
  UserRound,
} from "lucide-react";
import { cn } from "@/lib/utils";

const commands = [
  { href: "/", label: "Go to Today", group: "Navigate", icon: ListChecks },
  { href: "/companies", label: "Go to Companies", group: "Navigate", icon: Building2 },
  { href: "/jobs", label: "Go to Jobs", group: "Navigate", icon: Search },
  { href: "/profile", label: "Go to Profile", group: "Navigate", icon: UserRound },
  { href: "/settings", label: "Go to Settings", group: "Navigate", icon: Settings },
  { href: "/companies", label: "Import company CSV", group: "Actions", icon: Building2 },
  { href: "/jobs", label: "Review matches", group: "Actions", icon: Search },
  { href: "/settings?tab=notifications", label: "Tune notification thresholds", group: "Actions", icon: Mail },
];

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      const tag = target?.tagName.toLowerCase();
      if (tag === "input" || tag === "textarea" || tag === "select") return;
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen(true);
      }
      if (event.key === "/") {
        event.preventDefault();
        setOpen(true);
      }
      if (event.key === "Escape") setOpen(false);
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  useEffect(() => {
    if (open) window.setTimeout(() => inputRef.current?.focus(), 25);
  }, [open]);

  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return commands;
    return commands.filter(
      (command) =>
        command.label.toLowerCase().includes(normalized) ||
        command.group.toLowerCase().includes(normalized),
    );
  }, [query]);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="hidden h-8 w-[280px] max-w-[34vw] items-center gap-2 rounded-[3px] border border-[var(--line)] bg-[var(--bg-raised)] px-3 text-[12.5px] text-[var(--ink-3)] transition hover:border-[var(--line-strong)] hover:text-[var(--ink-2)] lg:flex"
      >
        <Search size={14} />
        <span className="truncate">Search or run command...</span>
        <span className="ml-auto rounded-[3px] border border-[var(--line)] bg-[var(--bg-sunken)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--ink-4)]">
          ⌘K
        </span>
      </button>

      <button
        type="button"
        onClick={() => setOpen(true)}
        className="inline-grid h-[30px] w-[30px] place-items-center rounded-[3px] text-[var(--ink-3)] transition hover:bg-[var(--bg-hover)] lg:hidden"
        aria-label="Open command palette"
      >
        <Search size={15} />
      </button>

      {open ? (
        <div
          className="fixed inset-0 z-50 bg-[rgba(26,24,21,0.3)] p-3 backdrop-blur-sm sm:p-8"
          onClick={() => setOpen(false)}
        >
          <div
            className="mx-auto mt-[12vh] max-w-xl overflow-hidden rounded-md border border-[var(--line)] bg-[var(--bg-raised)] shadow-[0_16px_48px_rgba(26,24,21,0.18)]"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="border-b border-[var(--line)]">
              <input
                ref={inputRef}
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search routes and commands..."
                className="h-14 w-full border-0 bg-transparent px-5 text-[15px] text-[var(--ink)] outline-none placeholder:text-[var(--ink-3)]"
              />
            </div>
            <div className="max-h-[420px] overflow-auto p-2">
              {filtered.map((command) => {
                const Icon = command.icon;
                return (
                  <Link
                    key={`${command.group}-${command.label}`}
                    href={command.href}
                    onClick={() => {
                      setOpen(false);
                      setQuery("");
                    }}
                    className={cn(
                      "flex items-center gap-3 rounded-[3px] px-3 py-2 text-[13px] text-[var(--ink-2)] transition hover:bg-[var(--accent-soft)] hover:text-[var(--accent-ink)]",
                    )}
                  >
                    <span className="flex h-5 w-5 items-center justify-center text-[var(--ink-3)]">
                      <Icon size={14} />
                    </span>
                    <span className="min-w-0 flex-1 truncate">{command.label}</span>
                    <span className="font-mono text-[10px] uppercase tracking-[0.1em] text-[var(--ink-4)]">
                      {command.group}
                    </span>
                  </Link>
                );
              })}
              {filtered.length === 0 ? (
                <div className="px-3 py-8 text-center text-sm text-[var(--ink-3)]">
                  No commands found.
                </div>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
