import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function PageSection({
  title,
  description,
  actions,
  children,
  className,
}: {
  title?: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={cn(
        "overflow-hidden rounded-md border border-[var(--line)] bg-[var(--bg-raised)]",
        className,
      )}
    >
      {title || description || actions ? (
        <div className="flex flex-col gap-3 border-b border-[var(--line)] px-5 py-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            {title ? (
              <h2 className="truncate text-sm font-medium text-[var(--ink)]">
                {title}
              </h2>
            ) : null}
            {description ? (
              <p className="mt-1 text-xs leading-5 text-[var(--ink-3)]">
                {description}
              </p>
            ) : null}
          </div>
          {actions ? <div className="shrink-0">{actions}</div> : null}
        </div>
      ) : null}
      {children}
    </section>
  );
}
