import { MetricCard } from "@/components/ui/metric-card";
import { PageSection } from "@/components/ui/page-section";
import { StatusBadge } from "@/components/ui/status-badge";
import type { Company } from "@/lib/api";

type CompanyHealthSummaryProps = {
  companies: Company[];
  backendOnline: boolean;
};

export function CompanyHealthSummary({
  companies,
  backendOnline,
}: CompanyHealthSummaryProps) {
  const active = companies.filter((company) => company.is_active).length;
  const monitored = companies.filter(
    (company) => company.source_health === "active",
  ).length;
  const failing = companies.filter((company) =>
    ["degraded", "failing", "blocked"].includes(company.source_health),
  ).length;
  const unscanned = companies.filter(
    (company) => company.source_health === "needs_setup",
  ).length;

  return (
    <PageSection
      title="Source health"
      actions={
          <StatusBadge tone={backendOnline ? "success" : "danger"} withDot>
            {backendOnline ? "Backend online" : "Backend down"}
          </StatusBadge>
      }
    >
      <div className="grid grid-cols-2 gap-3 p-3">
        <MetricCard label="Tracked" value={companies.length} detail="Companies" />
        <MetricCard label="Active" value={active} detail="Enabled sources" />
        <MetricCard label="Monitoring" value={monitored} detail="Sources active" />
        <MetricCard
          label="Needs work"
          value={failing + unscanned}
          detail={`${failing} failed, ${unscanned} unscanned`}
        />
      </div>
    </PageSection>
  );
}
