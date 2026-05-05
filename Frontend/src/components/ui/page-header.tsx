import type { ReactNode } from "react";

type PageHeaderProps = {
  title: string;
  eyebrow?: string;
  description?: string;
  actions?: ReactNode;
};

export function PageHeader({
  title,
  eyebrow,
  description,
  actions,
}: PageHeaderProps) {
  return (
    <div className="mb-4 flex flex-col gap-5 border-b border-[var(--line)] pb-8 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0">
        {eyebrow ? (
          <div className="font-mono text-[11px] font-medium uppercase tracking-[0.1em] text-[var(--ink-3)]">
            {eyebrow}
          </div>
        ) : null}
        <h1 className="mt-3 truncate font-serif text-[42px] font-normal leading-none tracking-[-0.015em] text-[var(--ink)]">
          {title}
        </h1>
        {description ? (
          <p className="mt-3 max-w-[56ch] text-[15px] leading-6 text-[var(--ink-2)]">
            {description}
          </p>
        ) : null}
      </div>
      {actions ? (
        <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>
      ) : null}
    </div>
  );
}
