import Link from "next/link";
import type { ReactNode } from "react";
import { AddCompanyForm } from "@/components/companies/add-company-form";
import {
  formatDateTime,
  formatRelativeScan,
  formatSourceType,
  formatWorkMode,
  getCompanyKeywordInputValue,
  getCompanyPriority,
  getCompanyWorkModeFilter,
  getScrapeStatusBadge,
} from "@/components/companies/company-utils";
import { RecentCompanyLogs } from "@/components/companies/recent-company-logs";
import { Button } from "@/components/ui/button";
import { DangerAction } from "@/components/ui/danger-action";
import { DataTable } from "@/components/ui/data-table";
import { DetailDrawer } from "@/components/ui/detail-drawer";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Input, Select } from "@/components/ui/form-controls";
import { MetricCard } from "@/components/ui/metric-card";
import { PageHeader } from "@/components/ui/page-header";
import { PageSection } from "@/components/ui/page-section";
import { StatusBadge } from "@/components/ui/status-badge";
import { SystemBanner } from "@/components/ui/system-banner";
import {
  getApiErrorMessage,
  getBackendApiBaseUrl,
  getBackendHealth,
  listCompanyLogs,
  listCompanies,
  toApiResult,
} from "@/lib/api";
import type { Company } from "@/lib/api";
import {
  addCompanyAction,
  deleteCompanyAction,
  generateCompanyIntelligenceAction,
  scrapeCompanyAction,
  toggleCompanyPausedAction,
  updateCompanyAction,
} from "./actions";

type CompaniesPageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function CompaniesPage({
  searchParams,
}: CompaniesPageProps) {
  const params = await searchParams;
  const companyError = getSearchParam(params, "company_error");
  const companyAdded = getSearchParam(params, "company_added") === "1";
  const scanStatus = getSearchParam(params, "scan_status");
  const jobsFound = getSearchParam(params, "jobs_found");
  const jobsCreated = getSearchParam(params, "jobs_created");
  const jobsUpdated = getSearchParam(params, "jobs_updated");
  const companyUpdated = getSearchParam(params, "company_updated") === "1";
  const companyPaused = getSearchParam(params, "company_paused") === "1";
  const companyResumed = getSearchParam(params, "company_resumed") === "1";
  const companyDeleted = getSearchParam(params, "company_deleted") === "1";
  const companyIntelligence = getSearchParam(params, "company_intelligence") === "1";
  const selectedCompanyId = Number(getSearchParam(params, "company_id"));

  const [healthResult, companiesResult, logsResult] = await Promise.all([
    toApiResult(getBackendHealth()),
    toApiResult(listCompanies()),
    toApiResult(listCompanyLogs({ limit: 8 })),
  ]);

  const backendOnline =
    healthResult.ok && String(healthResult.data.status).toLowerCase() === "ok";
  const companies = companiesResult.ok ? companiesResult.data.results : [];
  const logs = logsResult.ok ? logsResult.data.results : [];
  const logError = logsResult.ok ? undefined : getApiErrorMessage(logsResult.error);
  const selectedCompany =
    (Number.isInteger(selectedCompanyId)
      ? companies.find((company) => company.id === selectedCompanyId)
      : undefined) ?? companies[0];
  const active = companies.filter((company) => company.is_active).length;
  const failing = companies.filter((company) =>
    ["degraded", "failing", "blocked"].includes(company.source_health),
  ).length;
  const unscanned = companies.filter((company) => !company.last_scraped_at).length;

  return (
    <div className="space-y-4">
      <PageHeader
        title="Companies"
        eyebrow="Watchlist"
        description="Monitor favorite companies, source health, scan cadence, filters, and intelligence from one operational table."
        actions={
          <StatusBadge tone={backendOnline ? "success" : "danger"} withDot>
            {backendOnline ? "Backend online" : "Backend down"}
          </StatusBadge>
        }
      />

      {companyAdded ? <SystemBanner tone="success">Company added. Run a scan when you are ready to pull jobs.</SystemBanner> : null}
      {companyUpdated || companyPaused || companyResumed || companyDeleted || companyIntelligence ? (
        <SystemBanner tone="success">
          {companyUpdated
            ? "Company updated."
            : companyPaused
              ? "Company paused."
              : companyResumed
                ? "Company resumed."
                : companyDeleted
                  ? "Company deleted."
                  : "Company intelligence generated."}
        </SystemBanner>
      ) : null}
      {scanStatus ? (
        <SystemBanner tone="info">
          <span className="font-semibold">Scan finished:</span> {scanStatus}. Found {jobsFound ?? "0"}, created {jobsCreated ?? "0"}, updated {jobsUpdated ?? "0"}.
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
        <MetricCard label="Tracked" value={companies.length} detail="Total sources" />
        <MetricCard label="Active" value={active} detail="Enabled scans" />
        <MetricCard label="Needs work" value={failing} detail="Failing or degraded" />
        <MetricCard label="Unscanned" value={unscanned} detail="Ready for first scan" />
      </div>

      <AddCompanyForm action={addCompanyAction} />

      {!companiesResult.ok ? (
        <ErrorState
          title="Backend API is unavailable"
          message="Tracked companies could not be loaded. Start the backend or update BACKEND_API_BASE_URL, then reload this page."
          detail={`${getBackendApiBaseUrl()}\n${getApiErrorMessage(companiesResult.error)}`}
        />
      ) : (
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_480px]">
          <CompaniesWatchlist companies={companies} selectedCompany={selectedCompany} />
          <CompanyDrawer company={selectedCompany} />
        </div>
      )}

      <RecentCompanyLogs companies={companies} logs={logs} logError={logError} />
    </div>
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
    return (
      <EmptyState
        title="No tracked companies"
        message="Add a careers URL to start source monitoring."
      />
    );
  }

  return (
    <PageSection
      title="Companies Watchlist"
      description="Select a row to inspect filters, scan controls, and source health."
      actions={<StatusBadge tone="neutral">{companies.length} total</StatusBadge>}
    >
        <DataTable minWidth="940px">
          <thead className="bg-[var(--surface-recessed)] font-mono text-[10px] font-semibold uppercase tracking-[0.16em] text-[var(--faint)]">
            <tr>
              <th scope="col" className="px-4 py-3">Target organization</th>
              <th scope="col" className="px-4 py-3">Priority</th>
              <th scope="col" className="px-4 py-3">Source health</th>
              <th scope="col" className="px-4 py-3">Last scan</th>
              <th scope="col" className="px-4 py-3">New role alerts</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border)]">
            {companies.map((company) => {
              const sourceHealth = getScrapeStatusBadge(company);
              const priority = getCompanyPriority(company);
              const selected = company.id === selectedCompany?.id;

              return (
                <tr key={company.id} className={selected ? "bg-indigo-500/10" : "transition hover:bg-[var(--surface-hover)]"}>
                  <td className="px-4 py-3">
                    <Link href={`/companies?company_id=${company.id}`} className="block min-w-0">
                      <div className="flex items-center gap-3">
                        <span className={["h-8 w-1 rounded-full", selected ? "bg-indigo-300" : "bg-transparent"].join(" ")} />
                        <div className="min-w-0">
                          <div className="truncate font-semibold text-slate-50">{company.name}</div>
                          <div className="mt-1 max-w-72 truncate font-mono text-[11px] text-slate-600">
                            {formatSourceType(company.scraper_type)}
                          </div>
                        </div>
                      </div>
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge tone={priority.tone}>{priority.label}</StatusBadge>
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge tone={sourceHealth.tone} withDot>
                      {sourceHealth.label}
                    </StatusBadge>
                  </td>
                  <td className="px-4 py-3">
                    <div className="font-mono text-xs text-slate-300">{formatRelativeScan(company.last_scraped_at)}</div>
                    <div className="mt-1 text-xs text-slate-600">{formatDateTime(company.last_scraped_at)}</div>
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge tone={company.alert_new_roles ? "success" : "neutral"} withDot>
                      {company.alert_new_roles ? "Enabled" : "Off"}
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
      <DetailDrawer title="No company selected" subtitle="Add a company or select a watchlist row.">
        <p className="text-sm leading-6 text-slate-500">
          Company filters, scan controls, intelligence, and dangerous actions will appear here.
        </p>
      </DetailDrawer>
    );
  }

  const sourceHealth = getScrapeStatusBadge(company);
  const priority = getCompanyPriority(company);

  return (
    <DetailDrawer
      eyebrow={`Org / ${company.id}`}
      title={company.name}
      subtitle={company.careers_url}
      closeHref="/companies"
      footer={
        <div className="grid gap-2 sm:grid-cols-2">
          <form action={scrapeCompanyAction}>
            <input type="hidden" name="company_id" value={company.id} />
            <Button type="submit" variant="primary" className="w-full">
              Scan now
            </Button>
          </form>
          <form action={toggleCompanyPausedAction}>
            <input type="hidden" name="company_id" value={company.id} />
            <input type="hidden" name="operation" value={company.is_paused ? "resume" : "pause"} />
            <Button type="submit" className="w-full">
              {company.is_paused ? "Resume" : "Pause"}
            </Button>
          </form>
        </div>
      }
    >
      <div className="space-y-5">
        <div className="grid gap-3 sm:grid-cols-2">
          <CompanyStat label="Priority" value={<StatusBadge tone={priority.tone}>{priority.label}</StatusBadge>} />
          <CompanyStat label="Source health" value={<StatusBadge tone={sourceHealth.tone} withDot>{sourceHealth.label}</StatusBadge>} />
          <CompanyStat label="Work mode" value={formatWorkMode(getCompanyWorkModeFilter(company))} />
          <CompanyStat label="Scan frequency" value={`Every ${company.scan_frequency_hours || 24}h`} />
        </div>

        <PageSection title="Targeting filters" className="bg-[var(--surface-recessed)]">
          <form action={updateCompanyAction} className="grid gap-3 p-4">
            <input type="hidden" name="company_id" value={company.id} />
            <TextField label="Name" name="name" defaultValue={company.name} />
            <label className="block">
              <span className="text-xs font-medium text-slate-500">Priority</span>
              <Select name="priority_tier" defaultValue={company.priority_tier || company.priority || "normal"}>
                <option value="dream">Dream</option>
                <option value="high">High</option>
                <option value="normal">Normal</option>
                <option value="fallback">Fallback</option>
              </Select>
            </label>
            <label className="block">
              <span className="text-xs font-medium text-slate-500">Work mode</span>
              <Select name="work_mode_filter" defaultValue={getCompanyWorkModeFilter(company)}>
                <option value="">Any</option>
                <option value="remote">Remote</option>
                <option value="hybrid">Hybrid</option>
                <option value="onsite">Onsite</option>
              </Select>
            </label>
            <TextField label="Title keywords" name="title_keywords" defaultValue={getCompanyKeywordInputValue(company, "title_keywords")} />
            <TextField label="Negative title keywords" name="negative_title_keywords" defaultValue={getCompanyKeywordInputValue(company, "negative_title_keywords")} />
            <TextField label="Location keywords" name="location_keywords" defaultValue={getCompanyKeywordInputValue(company, "location_keywords")} />
            <TextField label="Scan every hours" name="scan_frequency_hours" defaultValue={String(company.scan_frequency_hours || 24)} type="number" />
            <label className="flex items-center gap-2 text-xs font-medium text-slate-400">
              <input name="alert_new_roles" type="checkbox" defaultChecked={company.alert_new_roles} className="h-4 w-4 rounded border-slate-700 bg-slate-950 text-indigo-400" />
              New-role alerts
            </label>
            <Button type="submit" variant="primary">
              Save filters
            </Button>
          </form>
        </PageSection>

        <section className="rounded-lg border border-slate-800 bg-slate-950 p-4">
          <div className="console-label">Intelligence</div>
          <p className="mt-3 text-sm leading-6 text-slate-400">
            {company.latest_intelligence?.summary || "No intelligence report generated yet."}
          </p>
          <form action={generateCompanyIntelligenceAction} className="mt-3">
            <input type="hidden" name="company_id" value={company.id} />
            <Button type="submit" size="sm">
              Generate intelligence report
            </Button>
          </form>
        </section>

        <DangerAction
          title="Danger zone"
          description="Deleting a company removes it from source monitoring."
        >
          <form action={deleteCompanyAction} className="mt-3 grid gap-2">
            <input type="hidden" name="company_id" value={company.id} />
            <Input name="delete_confirm" placeholder="Type DELETE" />
            <Button type="submit" variant="danger" size="sm">
              Delete company
            </Button>
          </form>
        </DangerAction>
      </div>
    </DetailDrawer>
  );
}

function TextField({
  label,
  name,
  defaultValue,
  type = "text",
}: {
  label: string;
  name: string;
  defaultValue: string;
  type?: string;
}) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-slate-500">{label}</span>
      <Input name={name} type={type} defaultValue={defaultValue} />
    </label>
  );
}

function CompanyStat({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="rounded-md border border-slate-800 bg-slate-950 px-3 py-2">
      <div className="console-label">{label}</div>
      <div className="mt-2 text-sm font-semibold text-slate-100">{value}</div>
    </div>
  );
}

function getSearchParam(
  params: Record<string, string | string[] | undefined>,
  key: string,
) {
  const value = params[key];
  return Array.isArray(value) ? value[0] : value;
}
