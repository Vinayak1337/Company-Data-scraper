import type { ReactNode } from "react";

type MetricCardProps = {
  label: string;
  value: ReactNode;
  detail?: ReactNode;
};

export function MetricCard({ label, value, detail }: MetricCardProps) {
  return (
    <div className="rounded-md border border-[var(--line)] bg-[var(--bg-raised)] p-6 transition hover:-translate-y-px hover:border-[var(--line-strong)]">
      <div className="font-mono text-[10px] font-medium uppercase tracking-[0.1em] text-[var(--ink-3)]">
        {label}
      </div>
      <div className="mt-3 font-serif text-[38px] font-normal leading-none tracking-[-0.02em] text-[var(--ink)] tabular-nums">
        {value}
      </div>
      {detail ? <div className="mt-3 text-xs text-[var(--ink-3)]">{detail}</div> : null}
    </div>
  );
}
