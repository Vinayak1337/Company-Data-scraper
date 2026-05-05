import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";
import { PageSection } from "@/components/ui/page-section";
import { StatusBadge } from "@/components/ui/status-badge";

type PlaceholderPageProps = {
  title: string;
  eyebrow: string;
  description: string;
  queuedItems: string[];
};

export function PlaceholderPage({
  title,
  eyebrow,
  description,
  queuedItems,
}: PlaceholderPageProps) {
  return (
    <div className="space-y-4">
      <PageHeader
        title={title}
        eyebrow={eyebrow}
        description={description}
        actions={<StatusBadge tone="neutral">Wave 1 placeholder</StatusBadge>}
      />

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
        <EmptyState
          title={`${title} workspace is staged`}
          message="This section is wired into the navigation shell and reserved for the next data-backed slice."
        />

        <PageSection title="Planned surface">
          <ul className="divide-y divide-[var(--border)]">
            {queuedItems.map((item) => (
              <li key={item} className="px-4 py-3 text-sm text-[var(--muted)]">
                {item}
              </li>
            ))}
          </ul>
        </PageSection>
      </div>
    </div>
  );
}
