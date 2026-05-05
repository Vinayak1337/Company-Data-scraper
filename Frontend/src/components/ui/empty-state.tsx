import type { ReactNode } from "react";

type EmptyStateProps = {
  title: string;
  message: string;
  action?: ReactNode;
};

export function EmptyState({ title, message, action }: EmptyStateProps) {
  return (
    <div className="rounded-lg border border-dashed border-[var(--border)] bg-[var(--surface-recessed)] px-4 py-8 text-center">
      <div className="text-sm font-semibold text-[var(--text)]">{title}</div>
      <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-[var(--muted)]">
        {message}
      </p>
      {action ? <div className="mt-4 flex justify-center">{action}</div> : null}
    </div>
  );
}
