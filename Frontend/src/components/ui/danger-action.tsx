import type { ReactNode } from "react";

export function DangerAction({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <section className="rounded-lg border border-[color-mix(in_srgb,var(--danger)_38%,transparent)] bg-[color-mix(in_srgb,var(--danger)_10%,transparent)]">
      <div className="border-b border-[color-mix(in_srgb,var(--danger)_26%,transparent)] px-4 py-3">
        <h2 className="text-sm font-semibold text-[var(--danger)]">{title}</h2>
        <p className="mt-1 text-xs leading-5 text-[var(--muted)]">{description}</p>
      </div>
      <div className="p-4">{children}</div>
    </section>
  );
}
