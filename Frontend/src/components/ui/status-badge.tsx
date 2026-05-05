import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

type StatusBadgeTone = "neutral" | "success" | "warning" | "danger" | "info";

const toneClasses: Record<StatusBadgeTone, string> = {
  neutral:
    "border-[var(--line)] bg-[var(--bg-sunken)] text-[var(--ink-2)]",
  success:
    "border-transparent bg-[var(--ok-soft)] text-[var(--ok)]",
  warning:
    "border-transparent bg-[var(--warn-soft)] text-[var(--warn)]",
  danger:
    "border-transparent bg-[var(--danger-soft)] text-[var(--danger)]",
  info:
    "border-transparent bg-[var(--accent-soft)] text-[var(--accent-ink)]",
};

const dotClasses: Record<StatusBadgeTone, string> = {
  neutral: "bg-[var(--faint)]",
  success: "bg-[var(--success)]",
  warning: "bg-[var(--warning)]",
  danger: "bg-[var(--danger)]",
  info: "bg-[var(--info)]",
};

type StatusBadgeProps = {
  children: ReactNode;
  tone?: StatusBadgeTone;
  withDot?: boolean;
  title?: string;
  className?: string;
};

export function StatusBadge({
  children,
  tone = "neutral",
  withDot = false,
  title,
  className,
}: StatusBadgeProps) {
  return (
    <span
      title={title}
      className={cn(
        "inline-flex h-6 max-w-full items-center gap-1.5 rounded-[3px] border px-2 font-mono text-[11px] font-medium leading-none tracking-[0.02em]",
        toneClasses[tone],
        className,
      )}
    >
      {withDot ? (
        <span className={cn("h-1.5 w-1.5 rounded-full", dotClasses[tone])} />
      ) : null}
      <span className="truncate">{children}</span>
    </span>
  );
}
