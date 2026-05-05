import Link from "next/link";
import type { ReactNode } from "react";
import { X } from "lucide-react";

type DetailDrawerProps = {
  eyebrow?: ReactNode;
  title: ReactNode;
  subtitle?: ReactNode;
  closeHref?: string;
  children: ReactNode;
  footer?: ReactNode;
};

export function DetailDrawer({
  eyebrow,
  title,
  subtitle,
  closeHref,
  children,
  footer,
}: DetailDrawerProps) {
  return (
    <aside className="flex min-h-[520px] min-w-0 flex-col rounded-md border border-[var(--line)] bg-[var(--bg-raised)] xl:sticky xl:top-20 xl:max-h-[calc(100vh-6rem)]">
      <div className="flex items-start justify-between gap-4 border-b border-[var(--border)] px-4 py-4">
        <div className="min-w-0">
          {eyebrow ? (
            <div className="font-mono text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--faint)]">
              {eyebrow}
            </div>
          ) : null}
          <h2 className="mt-1 truncate text-xl font-semibold tracking-tight text-[var(--text)]">
            {title}
          </h2>
          {subtitle ? (
            <div className="mt-1 break-words text-sm leading-6 text-[var(--muted)]">
              {subtitle}
            </div>
          ) : null}
        </div>
        {closeHref ? (
          <Link
            href={closeHref}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-[var(--border)] text-[var(--muted)] transition hover:bg-[var(--surface-hover)] hover:text-[var(--text)]"
            aria-label="Close details"
          >
            <X size={14} />
          </Link>
        ) : null}
      </div>
      <div className="min-h-0 flex-1 overflow-auto px-4 py-4">{children}</div>
      {footer ? (
        <div className="border-t border-[var(--border)] bg-[var(--surface-recessed)] px-4 py-3">
          {footer}
        </div>
      ) : null}
    </aside>
  );
}
