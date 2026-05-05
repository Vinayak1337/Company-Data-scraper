type ErrorStateProps = {
  title: string;
  message: string;
  detail?: string;
};

export function ErrorState({ title, message, detail }: ErrorStateProps) {
  return (
    <div className="rounded-lg border border-[color-mix(in_srgb,var(--danger)_38%,transparent)] bg-[color-mix(in_srgb,var(--danger)_10%,transparent)] px-4 py-3">
      <div className="text-sm font-semibold text-[var(--danger)]">{title}</div>
      <div className="mt-1 text-sm leading-6 text-[var(--muted)]">{message}</div>
      {detail ? (
        <pre className="mt-3 max-h-40 overflow-auto whitespace-pre-wrap rounded-md border border-[var(--border)] bg-[var(--surface-recessed)] px-3 py-2 font-mono text-xs leading-5 text-[var(--muted)]">
          {detail}
        </pre>
      ) : null}
    </div>
  );
}
