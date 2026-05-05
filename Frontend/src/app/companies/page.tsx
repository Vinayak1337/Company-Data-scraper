import Link from "next/link";
import type { InputHTMLAttributes } from "react";
import { AddCompanyForm } from "@/components/companies/add-company-form";
import { Button } from "@/components/ui/button";
import { DangerAction } from "@/components/ui/danger-action";
import { DataTable } from "@/components/ui/data-table";
import { DetailDrawer } from "@/components/ui/detail-drawer";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Input, Select, Textarea } from "@/components/ui/form-controls";
import { MetricCard } from "@/components/ui/metric-card";
import { PageHeader } from "@/components/ui/page-header";
import { PageSection } from "@/components/ui/page-section";
import { StatusBadge } from "@/components/ui/status-badge";
import { SystemBanner } from "@/components/ui/system-banner";
import {
  getApiErrorMessage,
  getBackendApiBaseUrl,
  getBackendHealth,
  listCompanies,
  listCrawlRuns,
  toApiResult,
} from "@/lib/api";
import type { Company, CrawlRun } from "@/lib/api";
import {
  addCompanyAction,
  addCompanySourceAction,
  crawlCompanyAction,
  deleteCompanyAction,
  discoverCompanySourceAction,
  importCompaniesCsvAction,
  toggleCompanyPausedAction,
  updateCompanyAction,
} from "./actions";

type CompaniesPageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function CompaniesPage({ searchParams }: CompaniesPageProps) {
  const params = await searchParams;
  const companyError = getSearchParam(params, "company_error");
  const companyNotice = getSearchParam(params, "company_notice");
  const selectedCompanyId = Number(getSearchParam(params, "company_id"));
  const crawlStatus = getSearchParam(params, "crawl_status");
  const jobsFound = getSearchParam(params, "jobs_found");
  const jobsCreated = getSearchParam(params, "jobs_created");
  const jobsUpdated = getSearchParam(params, "jobs_updated");

  const [healthResult, companiesResult, crawlsResult] = await Promise.all([
    toApiResult(getBackendHealth()),
    toApiResult(listCompanies()),
    toApiResult(listCrawlRuns({ limit: 8 })),
  ]);

  const backendOnline = healthResult.ok && String(healthResult.data.status).toLowerCase() === "ok";
  const companies = companiesResult.ok ? companiesResult.data.results : [];
  const crawlRuns = crawlsResult.ok ? crawlsResult.data.results : [];
  const selectedCompany =
    (Number.isInteger(selectedCompanyId)
      ? companies.find((company) => company.id === selectedCompanyId)
      : undefined) ?? companies[0];
  const active = companies.filter((company) => company.is_active).length;
  const needsSource = companies.filter((company) => ["needs_source", "needs_review"].includes(company.source_health)).length;
  const failing = companies.filter((company) => ["degraded", "failing", "blocked"].includes(company.source_health)).length;

  return (
    <div className="space-y-4">
      <PageHeader
        title="Companies"
        eyebrow="Watchlist"
        description="Import companies, verify their jobs source, toggle active crawls, and run discovery without extra CRM workflow."
        actions={
          <StatusBadge tone={backendOnline ? "success" : "danger"} withDot>
            {backendOnline ? "Backend online" : "Backend down"}
          </StatusBadge>
        }
      />

      {companyNotice ? <SystemBanner tone="success">{companyNotice}</SystemBanner> : null}
      {getSearchParam(params, "company_added") ? <SystemBanner tone="success">Company added.</SystemBanner> : null}
      {getSearchParam(params, "company_updated") ? <SystemBanner tone="success">Company updated.</SystemBanner> : null}
      {getSearchParam(params, "company_paused") ? <SystemBanner tone="success">Company paused.</SystemBanner> : null}
      {getSearchParam(params, "company_resumed") ? <SystemBanner tone="success">Company resumed.</SystemBanner> : null}
      {getSearchParam(params, "company_deleted") ? <SystemBanner tone="success">Company deleted.</SystemBanner> : null}
      {crawlStatus ? (
        <SystemBanner tone="info">
          <span className="font-semibold">Crawl finished:</span> {crawlStatus}. Found {jobsFound ?? "0"}, created {jobsCreated ?? "0"}, updated {jobsUpdated ?? "0"}.
        </SystemBanner>
      ) : null}
      {companyError ? (
        <ErrorState
          title="Company action failed"
          message={companyError}
          detail={`Backend API: ${getBackendApiBaseUrl()}`}
        />
      ) : null}

      <div className="grid gap-3 md:grid-cols-4">
        <MetricCard label="Tracked" value={companies.length} detail="Watchlist size" />
        <MetricCard label="Active" value={active} detail="Scheduled crawls" />
        <MetricCard label="Needs source" value={needsSource} detail="Discovery/review" />
        <MetricCard label="Failing" value={failing} detail="Crawl health" />
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
        <AddCompanyForm action={addCompanyAction} />
        <CsvImportPanel />
      </div>

      {!companiesResult.ok ? (
        <ErrorState
          title="Backend API is unavailable"
          message="Tracked companies could not be loaded."
          detail={`${getBackendApiBaseUrl()}\n${getApiErrorMessage(companiesResult.error)}`}
        />
      ) : (
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_480px]">
          <CompaniesWatchlist companies={companies} selectedCompany={selectedCompany} />
          <CompanyDrawer company={selectedCompany} />
        </div>
      )}

      <RecentCrawls crawlRuns={crawlRuns} error={crawlsResult.ok ? undefined : getApiErrorMessage(crawlsResult.error)} />
    </div>
  );
}

function CsvImportPanel() {
  return (
    <PageSection title="CSV import" description="Columns: company/name, domain, homepage_url, careers_url, priority, active, notes.">
      <form action={importCompaniesCsvAction} className="space-y-3 p-4">
        <Textarea
          name="company_csv"
          rows={7}
          className="font-mono text-xs leading-5"
          placeholder={"company,domain,active\nAcme,acme.com,true"}
        />
        <div className="flex justify-end">
          <Button type="submit" variant="primary">Import CSV</Button>
        </div>
      </form>
    </PageSection>
  );
}

function CompaniesWatchlist({
  companies,
  selectedCompany,
}: {
  companies: Company[];
  selectedCompany?: Company;
}) {
  if (companies.length === 0) {
    return <EmptyState title="No tracked companies" message="Import a CSV or add a company to start source discovery." />;
  }

  return (
    <PageSection title="Watchlist" description="Active companies with verified sources are included in scheduled crawls.">
      <DataTable minWidth="920px">
        <thead className="bg-[var(--surface-recessed)] font-mono text-[10px] font-semibold uppercase tracking-[0.16em] text-[var(--faint)]">
          <tr>
            <th scope="col" className="px-4 py-3">Company</th>
            <th scope="col" className="px-4 py-3">Source</th>
            <th scope="col" className="px-4 py-3">Health</th>
            <th scope="col" className="px-4 py-3">Last crawl</th>
            <th scope="col" className="px-4 py-3">State</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--border)]">
          {companies.map((company) => {
            const selected = company.id === selectedCompany?.id;
            return (
              <tr key={company.id} className={selected ? "bg-indigo-500/10" : "transition hover:bg-[var(--surface-hover)]"}>
                <td className="px-4 py-3">
                  <Link href={`/companies?company_id=${company.id}`} className="block min-w-0">
                    <div className="truncate font-semibold text-[var(--ink)]">{company.name}</div>
                    <div className="mt-1 truncate font-mono text-[11px] text-[var(--faint)]">{company.domain || company.homepage_url || "No domain"}</div>
                  </Link>
                </td>
                <td className="px-4 py-3">
                  <div className="truncate text-sm text-[var(--muted)]">{company.primary_source?.url || "Needs discovery"}</div>
                  <div className="mt-1 font-mono text-[11px] text-[var(--faint)]">{company.primary_source?.platform || company.source_discovery_status}</div>
                </td>
                <td className="px-4 py-3">
                  <StatusBadge tone={healthTone(company.source_health)} withDot>{labelize(company.source_health)}</StatusBadge>
                </td>
                <td className="px-4 py-3 font-mono text-xs text-[var(--muted)]">{formatDateTime(company.last_scraped_at)}</td>
                <td className="px-4 py-3">
                  <StatusBadge tone={company.is_active ? "success" : "neutral"} withDot>
                    {company.is_active ? "Active" : "Inactive"}
                  </StatusBadge>
                </td>
              </tr>
            );
          })}
        </tbody>
      </DataTable>
    </PageSection>
  );
}

function CompanyDrawer({ company }: { company?: Company }) {
  if (!company) {
    return (
      <DetailDrawer title="No company selected" subtitle="Add or import a company first.">
        <p className="text-sm leading-6 text-[var(--muted)]">Source discovery, manual source override, and crawl controls will appear here.</p>
      </DetailDrawer>
    );
  }

  return (
    <DetailDrawer
      eyebrow={`Company / ${company.id}`}
      title={company.name}
      subtitle={company.primary_source?.url || company.domain || "No jobs source yet"}
      closeHref="/companies"
      footer={
        <div className="grid gap-2 sm:grid-cols-2">
          <form action={crawlCompanyAction}>
            <input type="hidden" name="company_id" value={company.id} />
            <Button type="submit" variant="primary" className="w-full">Run now</Button>
          </form>
          <form action={discoverCompanySourceAction}>
            <input type="hidden" name="company_id" value={company.id} />
            <Button type="submit" className="w-full">Discover source</Button>
          </form>
        </div>
      }
    >
      <div className="space-y-4">
        <div className="grid gap-2 sm:grid-cols-3">
          <MetricCard label="Confidence" value={`${company.source_discovery_confidence}%`} detail="Source discovery" />
          <MetricCard label="Sources" value={company.sources.length} detail="Stored candidates" />
          <MetricCard label="Failures" value={company.consecutive_failure_count} detail="Consecutive" />
        </div>

        <PageSection title="Company settings">
          <form action={updateCompanyAction} className="grid gap-3 p-4">
            <input type="hidden" name="company_id" value={company.id} />
            <TextInput label="Name" name="name" defaultValue={company.name} />
            <TextInput label="Domain" name="domain" defaultValue={company.domain} />
            <TextInput label="Homepage URL" name="homepage_url" defaultValue={company.homepage_url} />
            <label>
              <span className="text-xs font-medium text-[var(--muted)]">Priority</span>
              <Select name="priority_tier" defaultValue={company.priority_tier}>
                <option value="dream">Dream</option>
                <option value="high">High</option>
                <option value="normal">Normal</option>
                <option value="fallback">Fallback</option>
              </Select>
            </label>
            <label>
              <span className="text-xs font-medium text-[var(--muted)]">Work mode</span>
              <Select name="work_mode_filter" defaultValue={company.work_mode_filter || "any"}>
                <option value="any">Any</option>
                <option value="remote">Remote</option>
                <option value="hybrid">Hybrid</option>
                <option value="onsite">Onsite</option>
              </Select>
            </label>
            <TextInput label="Scan frequency hours" name="scan_frequency_hours" type="number" defaultValue={String(company.scan_frequency_hours)} />
            <TextInput label="Target title keywords" name="title_keywords" defaultValue={listValue(company.title_keywords)} />
            <TextInput label="Negative title keywords" name="negative_title_keywords" defaultValue={listValue(company.negative_title_keywords)} />
            <TextInput label="Location keywords" name="location_keywords" defaultValue={listValue(company.location_keywords)} />
            <label className="flex items-center gap-2 text-sm text-[var(--muted)]">
              <input name="alert_new_roles" type="checkbox" defaultChecked={company.alert_new_roles} />
              Email/digest new matching roles
            </label>
            <label>
              <span className="text-xs font-medium text-[var(--muted)]">Notes</span>
              <Textarea name="notes" defaultValue={company.notes} rows={3} />
            </label>
            <div className="flex justify-end">
              <Button type="submit" variant="primary">Save</Button>
            </div>
          </form>
        </PageSection>

        <PageSection title="Manual source override">
          <form action={addCompanySourceAction} className="grid gap-3 p-4">
            <input type="hidden" name="company_id" value={company.id} />
            <TextInput label="Jobs source URL" name="source_url" defaultValue={company.primary_source?.url || company.careers_url} />
            <Button type="submit">Set primary source</Button>
          </form>
        </PageSection>

        <PageSection title="Sources">
          <div className="divide-y divide-[var(--border)]">
            {company.sources.length === 0 ? (
              <div className="p-4 text-sm text-[var(--muted)]">No sources discovered yet.</div>
            ) : (
              company.sources.map((source) => (
                <div key={source.id} className="p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <div className="truncate text-sm font-medium text-[var(--ink)]">{source.url}</div>
                      <div className="mt-1 font-mono text-[11px] text-[var(--faint)]">{source.platform} · {source.discovery_method}</div>
                    </div>
                    <StatusBadge tone={source.status === "active" ? "success" : "warning"}>{source.confidence_score}%</StatusBadge>
                  </div>
                </div>
              ))
            )}
          </div>
        </PageSection>

        <PageSection title="Activation">
          <form action={toggleCompanyPausedAction} className="grid gap-2 p-4 sm:grid-cols-2">
            <input type="hidden" name="company_id" value={company.id} />
            <Button type="submit" name="operation" value={company.is_active ? "pause" : "resume"}>
              {company.is_active ? "Set inactive" : "Set active"}
            </Button>
          </form>
        </PageSection>

        <DangerAction
          title="Delete company"
          description="Remove this company, sources, jobs, matches, and crawl history."
        >
          <form action={deleteCompanyAction} className="grid gap-3">
            <input type="hidden" name="company_id" value={company.id} />
            <TextInput label="Type DELETE" name="delete_confirm" />
            <div className="flex justify-end">
              <Button type="submit" variant="danger">Delete company</Button>
            </div>
          </form>
        </DangerAction>
      </div>
    </DetailDrawer>
  );
}

function RecentCrawls({ crawlRuns, error }: { crawlRuns: CrawlRun[]; error?: string }) {
  return (
    <PageSection title="Recent crawls" description="Latest manual or scheduled company crawls.">
      {error ? <ErrorState title="Crawls unavailable" message={error} /> : null}
      {crawlRuns.length === 0 ? (
        <div className="p-4 text-sm text-[var(--muted)]">No crawl runs yet.</div>
      ) : (
        <div className="divide-y divide-[var(--border)]">
          {crawlRuns.map((crawl) => (
            <div key={crawl.id} className="grid gap-2 p-4 md:grid-cols-[minmax(0,1fr)_120px_180px] md:items-center">
              <div className="min-w-0">
                <div className="truncate text-sm font-medium text-[var(--ink)]">{crawl.company_name}</div>
                <div className="mt-1 truncate font-mono text-[11px] text-[var(--faint)]">{crawl.source_url || crawl.source_platform}</div>
              </div>
              <StatusBadge tone={crawl.status === "success" ? "success" : crawl.status === "failed" ? "danger" : "neutral"}>{labelize(crawl.status)}</StatusBadge>
              <div className="font-mono text-xs text-[var(--muted)]">Found {crawl.jobs_found}, created {crawl.jobs_created}</div>
            </div>
          ))}
        </div>
      )}
    </PageSection>
  );
}

function TextInput({
  label,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & { label: string }) {
  return (
    <label>
      <span className="text-xs font-medium text-[var(--muted)]">{label}</span>
      <Input {...props} />
    </label>
  );
}

function listValue(value: string[] | string | null | undefined) {
  return Array.isArray(value) ? value.join(", ") : value || "";
}

function labelize(value: string) {
  return value.replace(/_/g, " ");
}

function healthTone(value: string): "neutral" | "success" | "warning" | "danger" | "info" {
  if (["active", "found"].includes(value)) return "success";
  if (["needs_source", "needs_review", "needs_setup", "degraded"].includes(value)) return "warning";
  if (["failing", "blocked", "failed"].includes(value)) return "danger";
  return "neutral";
}

function formatDateTime(value: string | null) {
  if (!value) return "Never";
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function getSearchParam(
  params: Record<string, string | string[] | undefined>,
  key: string,
) {
  const value = params[key];
  return Array.isArray(value) ? value[0] : value;
}
