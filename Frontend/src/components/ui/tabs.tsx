import Link from "next/link";

type TabItem = {
  href: string;
  label: string;
  active?: boolean;
};

export function Tabs({ items }: { items: TabItem[] }) {
  return (
    <nav
      aria-label="Section tabs"
      className="flex gap-1 overflow-x-auto border-b border-[var(--border)]"
    >
      {items.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          className={[
            "shrink-0 border-b-2 px-3 py-2 text-sm font-medium transition",
            item.active
              ? "border-[var(--primary)] text-[var(--primary)]"
              : "border-transparent text-[var(--muted)] hover:text-[var(--text)]",
          ].join(" ")}
        >
          {item.label}
        </Link>
      ))}
    </nav>
  );
}
