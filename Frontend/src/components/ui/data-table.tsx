import type { ReactNode } from "react";

export function DataTable({
  children,
  minWidth = "900px",
}: {
  children: ReactNode;
  minWidth?: string;
}) {
  return (
    <div className="overflow-hidden rounded-md border border-[var(--line)] bg-[var(--bg-raised)]">
      <div className="overflow-x-auto">
        <table
          className="w-full divide-y divide-[var(--line)] text-left text-[13px]"
          style={{ minWidth }}
        >
          {children}
        </table>
      </div>
    </div>
  );
}
