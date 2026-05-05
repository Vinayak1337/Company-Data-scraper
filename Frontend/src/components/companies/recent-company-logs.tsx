import { DataTable } from "@/components/ui/data-table";
import { PageSection } from "@/components/ui/page-section";
import { StatusBadge } from "@/components/ui/status-badge";
import type { Company, CompanyLog } from "@/lib/api";
import { formatDateTime, formatRelativeScan } from "./company-utils";

type RecentCompanyLogsProps = {
  companies: Company[];
  logs: CompanyLog[];
  logError?: string;
};

type DisplayLog = {
  id: string;
  companyName: string;
  status: string;
  sourcePlatform: string;
  jobsFound: number;
  jobsCreated: number;
  jobsUpdated: number;
  message: string;
  startedAt: string | null;
  finishedAt: string | null;
  isFallback: boolean;
};

export function RecentCompanyLogs({
  companies,
  logs,
  logError,
}: RecentCompanyLogsProps) {
  const displayLogs =
    logs.length > 0 ? normalizeLogs(logs, companies) : fallbackLogs(companies);

  return (
    <PageSection
      title="Recent scan logs"
      description={
        logError
          ? "Live log endpoint unavailable; showing scan snapshots."
          : `${displayLogs.length} recent`
      }
    >
      {displayLogs.length === 0 ? (
        <div className="px-4 py-6 text-sm text-[var(--muted)]">
          No scan logs recorded yet.
        </div>
      ) : (
        <DataTable minWidth="900px">
            <thead className="bg-[var(--surface-recessed)] font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--faint)]">
              <tr>
                <th scope="col" className="px-4 py-2.5">
                  Company
                </th>
                <th scope="col" className="px-4 py-2.5">
                  Status
                </th>
                <th scope="col" className="px-4 py-2.5">
                  Jobs
                </th>
                <th scope="col" className="px-4 py-2.5">
                  Message
                </th>
                <th scope="col" className="px-4 py-2.5">
                  Started
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {displayLogs.map((log) => (
                <tr key={log.id} className="align-top transition hover:bg-[var(--surface-hover)]">
                  <td className="px-4 py-2.5">
                    <div className="font-medium text-[var(--text)]">
                      {log.companyName}
                    </div>
                    <div className="mt-1 text-xs text-[var(--faint)]">
                      {log.sourcePlatform || "Unknown source"}
                    </div>
                  </td>
                  <td className="px-4 py-2.5">
                    <StatusBadge tone={statusTone(log.status)} withDot>
                      {log.status || "Unknown"}
                    </StatusBadge>
                  </td>
                  <td className="px-4 py-2.5 text-xs leading-5 text-[var(--muted)]">
                    <div>Found {log.jobsFound}</div>
                    <div>
                      Created {log.jobsCreated}, updated {log.jobsUpdated}
                    </div>
                  </td>
                  <td className="px-4 py-2.5">
                    <div className="max-w-xl text-xs leading-5 text-[var(--muted)]">
                      {log.message || "No message recorded."}
                      {log.isFallback ? (
                        <span className="ml-1 text-[var(--faint)]">
                          Snapshot
                        </span>
                      ) : null}
                    </div>
                  </td>
                  <td className="px-4 py-2.5">
                    <div className="text-xs font-medium text-[var(--muted)]">
                      {formatDateTime(log.startedAt)}
                    </div>
                    <div className="mt-1 text-xs text-[var(--faint)]">
                      {formatRelativeScan(log.finishedAt ?? log.startedAt)}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
        </DataTable>
      )}
    </PageSection>
  );
}

function normalizeLogs(logs: CompanyLog[], companies: Company[]): DisplayLog[] {
  const companiesById = new Map(
    companies.map((company) => [company.id, company.name]),
  );

  return logs.map((log) => ({
    id: `log-${log.id}`,
    companyName:
      log.company?.name ??
      log.company_name ??
      (log.company_id ? companiesById.get(log.company_id) : undefined) ??
      "Unknown company",
    status: log.status,
    sourcePlatform: log.source_platform,
    jobsFound: log.jobs_found,
    jobsCreated: log.jobs_created,
    jobsUpdated: log.jobs_updated,
    message: log.message,
    startedAt: log.started_at,
    finishedAt: log.finished_at,
    isFallback: false,
  }));
}

function fallbackLogs(companies: Company[]): DisplayLog[] {
  return companies
    .filter((company) => company.last_scraped_at)
    .sort((a, b) => {
      const left = new Date(a.last_scraped_at ?? 0).getTime();
      const right = new Date(b.last_scraped_at ?? 0).getTime();
      return right - left;
    })
    .slice(0, 8)
    .map((company) => ({
      id: `company-${company.id}`,
      companyName: company.name,
      status: company.last_scrape_status,
      sourcePlatform: company.scraper_type,
      jobsFound: 0,
      jobsCreated: 0,
      jobsUpdated: 0,
      message: company.last_scrape_message,
      startedAt: company.last_scraped_at,
      finishedAt: company.last_scraped_at,
      isFallback: true,
    }));
}

function statusTone(status: string) {
  switch (status) {
    case "success":
      return "success" as const;
    case "failed":
      return "danger" as const;
    case "running":
      return "info" as const;
    default:
      return "neutral" as const;
  }
}
