import { cn } from "@/lib/utils";

export function ScoreBar({
  value,
  max = 100,
  className,
}: {
  value: number;
  max?: number;
  className?: string;
}) {
  const percent = Math.max(0, Math.min(100, Math.round((value / max) * 100)));
  const tone =
    percent >= 80
      ? "bg-[var(--success)]"
      : percent >= 60
        ? "bg-[var(--warning)]"
        : "bg-[var(--danger)]";

  return (
    <div
      className={cn(
        "h-1.5 overflow-hidden rounded-full bg-[var(--surface-hover)]",
        className,
      )}
      aria-hidden="true"
    >
      <div className={cn("h-full rounded-full", tone)} style={{ width: `${percent}%` }} />
    </div>
  );
}
