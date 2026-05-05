import Link from "next/link";
import { Button, ButtonLink } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";
import { Input } from "@/components/ui/form-controls";
import { MetricCard } from "@/components/ui/metric-card";
import { PageHeader } from "@/components/ui/page-header";
import { PageSection } from "@/components/ui/page-section";
import { StatusBadge } from "@/components/ui/status-badge";
import { SystemBanner } from "@/components/ui/system-banner";
import {
  getApiErrorMessage,
  getBackendHealth,
  getDiagnostics,
  getNotificationPreferences,
  getProfile,
  listAgentRuns,
  listCompanies,
  listCrawlRuns,
  listJobs,
  toApiResult,
} from "@/lib/api";
import type { AgentRun, Company, CrawlRun, JobRecord } from "@/lib/api";
import { runAgentAction, runDueCrawlsAction } from "./actions";

type TodayPageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function TodayPage({ searchParams }: TodayPageProps) {
  const params = await searchParams;
  const todayNotice = getSearchParam(params, "today_notice");
  const todayError = getSearchParam(params, "today_error");

  const [healthResult, diagnosticsResult, profileResult, preferencesResult, companiesResult, jobsResult, crawlsResult, agentRunsResult] =
    await Promise.all([
      toApiResult(getBackendHealth()),
      toApiResult(getDiagnostics()),
      toApiResult(getProfile()),
      toApiResult(getNotificationPreferences()),
      toApiResult(listCompanies()),
      toApiResult(listJobs({ strong_fit_first: true, limit: 12 })),
      toApiResult(listCrawlRuns({ limit: 8 })),
      toApiResult(listAgentRuns(5)),
    ]);

  const backendOnline = healthResult.ok && String(healthResult.data.status).toLowerCase() === "ok";
  const diagnostics = diagnosticsResult.ok ? diagnosticsResult.data : null;
  const profile = profileResult.ok ? profileResult.data : null;
  const preferences = preferencesResult.ok ? preferencesResult.data : null;
  const companies = companiesResult.ok ? companiesResult.data.results : [];
  const jobs = jobsResult.ok ? jobsResult.data.results : [];
  const crawlRuns = crawlsResult.ok ? crawlsResult.data.results : [];
  const agentRuns = agentRunsResult.ok ? agentRunsResult.data.results : [];
  const notifyJobs = jobs.filter((job) => job.match.should_notify);
  const needsSource = companies.filter((company) => ["needs_source", "needs_review"].includes(company.source_health));

  return (
    <div className="space-y-4">
      <PageHeader
        title="Today"
        eyebrow="V3 loop"
        description="Setup readiness, company source health, crawl controls, and the newest jobs selected for notification."
        actions={
          <StatusBadge tone={backendOnline ? "success" : "danger"} withDot>
            {backendOnline ? "Backend online" : "Backend down"}
          </StatusBadge>
        }
      />

      {todayNotice ? <SystemBanner tone="success">{todayNotice}</SystemBanner> : null}
      {todayError ? <ErrorState title="Today action failed" message={todayError} /> : null}
      {!diagnosticsResult.ok ? (
        <ErrorState title="Diagnostics unavailable" message={getApiErrorMessage(diagnosticsResult.error)} />
      ) : null}

      <div className="grid gap-3 md:grid-cols-4">
        <MetricCard label="Companies" value={diagnostics?.counts.companies ?? companies.length} detail={`${diagnostics?.counts.active_companies ?? 0} active`} />
        <MetricCard label="Needs source" value={diagnostics?.counts.companies_needing_source ?? needsSource.length} detail="Discovery/review" />
        <MetricCard label="Jobs" value={diagnostics?.counts.jobs ?? jobs.length} detail="Discovered" />
        <MetricCard label="Notify" value={diagnostics?.counts.matches_to_notify ?? notifyJobs.length} detail="Above threshold" />
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
        <SetupChecklist
          profileComplete={diagnostics?.setup.profile_complete ?? false}
          aiConfigured={diagnostics?.setup.ai_configured ?? false}
          notificationsConfigured={diagnostics?.setup.notifications_configured ?? false}
          watchlistReady={diagnostics?.setup.company_watchlist_ready ?? false}
          profileScore={profile?.profile_completeness_score ?? 0}
          email={preferences?.email_address ?? ""}
        />
        <ControlPanel />
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
        <MatchesPanel jobs={notifyJobs.length ? notifyJobs : jobs.slice(0, 6)} />
        <NeedsSourcePanel companies={needsSource} />
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <RecentCrawls crawlRuns={crawlRuns} />
        <RecentAgents runs={agentRuns} />
      </div>
    </div>
  );
}

function SetupChecklist({
  profileComplete,
  aiConfigured,
  notificationsConfigured,
  watchlistReady,
  profileScore,
  email,
}: {
  profileComplete: boolean;
  aiConfigured: boolean;
  notificationsConfigured: boolean;
  watchlistReady: boolean;
  profileScore: number;
  email: string;
}) {
  const items = [
    { label: `Profile ${profileScore}%`, done: profileComplete, href: "/profile" },
    { label: "AI provider", done: aiConfigured, href: "/settings?tab=ai" },
    { label: email ? `Email ${email}` : "Email notifications", done: notificationsConfigured, href: "/settings?tab=notifications" },
    { label: "Company watchlist", done: watchlistReady, href: "/companies" },
  ];

  return (
    <PageSection title="Setup checklist" description="Crawling can run before setup is complete, but notifications should wait for profile, AI, email, and watchlist readiness.">
      <div className="divide-y divide-[var(--border)]">
        {items.map((item) => (
          <Link key={item.label} href={item.href} className="flex items-center justify-between gap-3 px-4 py-3 transition hover:bg-[var(--surface-hover)]">
            <span className="text-sm font-medium text-[var(--ink)]">{item.label}</span>
            <StatusBadge tone={item.done ? "success" : "warning"} withDot>
              {item.done ? "Done" : "Required"}
            </StatusBadge>
          </Link>
        ))}
      </div>
    </PageSection>
  );
}

function ControlPanel() {
  return (
    <PageSection title="Controls" description="Run due crawls or ask the local agent layer to review source and match decisions.">
      <div className="space-y-3 p-4">
        <form action={runDueCrawlsAction} className="flex items-end gap-2">
          <label className="min-w-0 flex-1">
            <span className="text-xs font-medium text-[var(--muted)]">Due crawl limit</span>
            <Input name="limit" type="number" min="1" max="100" defaultValue="10" />
          </label>
          <Button type="submit" variant="primary">Run due</Button>
        </form>
        <div className="grid gap-2 sm:grid-cols-2">
          <AgentButton agentType="source_discovery" label="Review sources" />
          <AgentButton agentType="match_review" label="Review matches" />
          <AgentButton agentType="notification_review" label="Review notifications" />
          <ButtonLink href="/companies" variant="default">Import CSV</ButtonLink>
        </div>
      </div>
    </PageSection>
  );
}

function AgentButton({ agentType, label }: { agentType: string; label: string }) {
  return (
    <form action={runAgentAction}>
      <input type="hidden" name="agent_type" value={agentType} />
      <Button type="submit" className="w-full">{label}</Button>
    </form>
  );
}

function MatchesPanel({ jobs }: { jobs: JobRecord[] }) {
  return (
    <PageSection title="Newest useful matches" description="Jobs selected for notification appear first.">
      {jobs.length === 0 ? (
        <div className="p-4 text-sm text-[var(--muted)]">No jobs yet. Import companies and run crawls to build the match inbox.</div>
      ) : (
        <div className="divide-y divide-[var(--border)]">
          {jobs.map((job) => (
            <Link key={job.id} href={`/jobs?job_id=${job.id}`} className="block px-4 py-3 transition hover:bg-[var(--surface-hover)]">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="truncate text-sm font-semibold text-[var(--ink)]">{job.title}</div>
                  <div className="mt-1 truncate text-xs text-[var(--muted)]">{job.company_name} · {job.location || "Unknown location"}</div>
                </div>
                <StatusBadge tone={job.match.should_notify ? "success" : "neutral"}>{job.match.overall_score}%</StatusBadge>
              </div>
              <p className="mt-2 line-clamp-2 text-xs leading-5 text-[var(--muted)]">{job.match.agent_summary}</p>
            </Link>
          ))}
        </div>
      )}
    </PageSection>
  );
}

function NeedsSourcePanel({ companies }: { companies: Company[] }) {
  return (
    <PageSection title="Companies needing source review" description="AI/source discovery candidates that need confirmation.">
      {companies.length === 0 ? (
        <div className="p-4 text-sm text-[var(--muted)]">No companies need source review.</div>
      ) : (
        <div className="divide-y divide-[var(--border)]">
          {companies.slice(0, 8).map((company) => (
            <Link key={company.id} href={`/companies?company_id=${company.id}`} className="flex items-center justify-between gap-3 px-4 py-3 transition hover:bg-[var(--surface-hover)]">
              <span className="min-w-0 truncate text-sm font-medium text-[var(--ink)]">{company.name}</span>
              <StatusBadge tone="warning">{company.source_discovery_confidence}%</StatusBadge>
            </Link>
          ))}
        </div>
      )}
    </PageSection>
  );
}

function RecentCrawls({ crawlRuns }: { crawlRuns: CrawlRun[] }) {
  return (
    <PageSection title="Recent crawls">
      {crawlRuns.length === 0 ? (
        <div className="p-4 text-sm text-[var(--muted)]">No crawl runs yet.</div>
      ) : (
        <div className="divide-y divide-[var(--border)]">
          {crawlRuns.map((run) => (
            <div key={run.id} className="flex items-center justify-between gap-3 px-4 py-3">
              <div className="min-w-0">
                <div className="truncate text-sm font-medium text-[var(--ink)]">{run.company_name}</div>
                <div className="mt-1 font-mono text-[11px] text-[var(--faint)]">Found {run.jobs_found}, created {run.jobs_created}</div>
              </div>
              <StatusBadge tone={run.status === "success" ? "success" : run.status === "failed" ? "danger" : "neutral"}>{run.status}</StatusBadge>
            </div>
          ))}
        </div>
      )}
    </PageSection>
  );
}

function RecentAgents({ runs }: { runs: AgentRun[] }) {
  return (
    <PageSection title="Recent agent reviews">
      {runs.length === 0 ? (
        <div className="p-4 text-sm text-[var(--muted)]">No agent reviews yet.</div>
      ) : (
        <div className="divide-y divide-[var(--border)]">
          {runs.map((run) => (
            <div key={run.id} className="px-4 py-3">
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm font-medium text-[var(--ink)]">{run.agent_type.replace(/_/g, " ")}</span>
                <StatusBadge tone={run.status === "success" ? "success" : run.status === "failed" ? "danger" : "neutral"}>{run.status}</StatusBadge>
              </div>
              <p className="mt-1 line-clamp-2 text-xs leading-5 text-[var(--muted)]">{run.result_summary || run.user_safe_error || "No summary yet."}</p>
            </div>
          ))}
        </div>
      )}
    </PageSection>
  );
}

function getSearchParam(
  params: Record<string, string | string[] | undefined>,
  key: string,
) {
  const value = params[key];
  return Array.isArray(value) ? value[0] : value;
}
