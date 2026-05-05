import type { ReactNode } from "react";
import { StatusBadge } from "./status-badge";

type SystemBannerTone = "success" | "info" | "warning" | "danger";

const labels: Record<SystemBannerTone, string> = {
  success: "Done",
  info: "Info",
  warning: "Review",
  danger: "Error",
};

type SystemBannerProps = {
  tone?: SystemBannerTone;
  children: ReactNode;
};

export function SystemBanner({ tone = "info", children }: SystemBannerProps) {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-sm leading-6 text-[var(--muted)]">
      <StatusBadge tone={tone} withDot>
        {labels[tone]}
      </StatusBadge>
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}
