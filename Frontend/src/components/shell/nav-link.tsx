"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BriefcaseBusiness,
  Building2,
  LayoutDashboard,
  Settings,
  UserRound,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";

const iconMap: Record<string, LucideIcon> = {
  today: LayoutDashboard,
  companies: Building2,
  jobs: BriefcaseBusiness,
  profile: UserRound,
  settings: Settings,
};

type NavLinkProps = {
  href: string;
  label: string;
  shortcut?: string;
  icon?: keyof typeof iconMap;
};

export function NavLink({ href, label, shortcut, icon }: NavLinkProps) {
  const pathname = usePathname();
  const isActive = href === "/" ? pathname === "/" : pathname.startsWith(href);
  const Icon = icon ? iconMap[icon] : undefined;

  return (
    <Link
      href={href}
      className={cn(
        "group flex items-center justify-between rounded-[3px] border px-2 py-[7px] text-[13.5px] font-normal transition",
        isActive
          ? "border-[var(--line)] bg-[var(--bg-raised)] text-[var(--ink)] shadow-sm"
          : "border-transparent text-[var(--ink-2)] hover:bg-[var(--bg-hover)] hover:text-[var(--ink)]",
      )}
    >
      <span className="flex min-w-0 items-center gap-2">
        {Icon ? (
          <span
            aria-hidden="true"
            className={cn(
              "flex h-4 w-4 shrink-0 items-center justify-center",
              isActive
                ? "text-[var(--accent)]"
                : "text-[var(--ink-3)] group-hover:text-[var(--ink-2)]",
            )}
          >
            <Icon size={13} />
          </span>
        ) : null}
        <span className="truncate">{label}</span>
      </span>
      {shortcut ? (
        <span
          className={cn(
            "ml-3 rounded-[3px] border px-1.5 py-0.5 font-mono text-[10px] font-medium uppercase leading-none",
            isActive
              ? "border-[var(--line)] bg-[var(--bg-sunken)] text-[var(--ink-4)]"
              : "border-[var(--line)] bg-[var(--bg-sunken)] text-[var(--ink-4)] group-hover:text-[var(--ink-3)]",
          )}
        >
          {shortcut}
        </span>
      ) : null}
    </Link>
  );
}
