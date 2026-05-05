import Link from "next/link";
import { Button, ButtonLink } from "@/components/ui/button";
import { DetailDrawer } from "@/components/ui/detail-drawer";
import { ErrorState } from "@/components/ui/error-state";
import { Input, Select, Textarea } from "@/components/ui/form-controls";
import { MetricCard } from "@/components/ui/metric-card";
import { PageHeader } from "@/components/ui/page-header";
import { ScoreBar } from "@/components/ui/score-bar";
import { StatusBadge } from "@/components/ui/status-badge";
import { SystemBanner } from "@/components/ui/system-banner";
import { getApiErrorMessage, listCompanies, listJobs, toApiResult } from "@/lib/api";
import type { JobRecord } from "@/lib/api";
import { submitJobFeedbackAction } from "./actions";

type JobsPageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function JobsPage({ searchParams }: JobsPageProps) {
  const params = await searchParams;
  const query = getSearchParam(params, "q");
  const priority = getSearchParam(params, "priority");
  const companyId = Number(getSearchParam(params, "company"));
  const notice = getSearchParam(params, "jobs_notice");
  const error = getSearchParam(params, "jobs_error");
  const selectedJobId = Number(getSearchParam(params, "job_id"));

  const [jobsResult, companiesResult] = await Promise.all([
    toApiResult(
      listJobs({
        q: query,
        company: Number.isInteger(companyId) && companyId > 0 ? companyId : undefined,
        strong_fit_first: true,
      }),
    ),
    toApiResult(listCompanies()),
  ]);

  const jobs = jobsResult.ok ? jobsResult.data.results : [];
  const companies = companiesResult.ok ? companiesResult.data.results : [];
  const filteredJobs = priority ? jobs.filter((job) => job.match.apply_priority === priority) : jobs;
  const selectedJob =
    (Number.isInteger(selectedJobId)
      ? filteredJobs.find((job) => job.id === selectedJobId)
      : undefined) ?? filteredJobs[0];
  const notifyCount = jobs.filter((job) => job.match.should_notify).length;
  const applyNowCount = jobs.filter((job) => job.match.apply_priority === "apply_now").length;
  const heldCount = jobs.length - notifyCount;

  return (
    <div className="space-y-4">
      <PageHeader
        title="Jobs"
        eyebrow="Match inbox"
        description="Review discovered jobs by match score, evidence, AI/local agent summary, and feedback controls."
        actions={<StatusBadge tone="info" withDot>Weighted scorer</StatusBadge>}
      />

      {notice ? <SystemBanner tone="success">{notice}</SystemBanner> : null}
      {error ? <ErrorState title="Job action failed" message={error} /> : null}
      {!jobsResult.ok ? (
        <ErrorState
          title="Backend API is unavailable"
          message="Jobs could not be loaded."
          detail={getApiErrorMessage(jobsResult.error)}
        />
      ) : null}

      <div className="grid gap-3 md:grid-cols-4">
        <MetricCard label="Jobs" value={jobs.length} detail="Discovered roles" />
        <MetricCard label="Notify" value={notifyCount} detail="Cleared threshold" />
        <MetricCard label="Apply now" value={applyNowCount} detail="Highest priority" />
        <MetricCard label="Held" value={heldCount} detail="Below threshold" />
      </div>

      <FilterPanel query={query} priority={priority} companies={companies} companyId={companyId} />

      <div className="grid min-w-0 gap-4 xl:grid-cols-[minmax(0,1fr)_500px]">
        <JobsReviewList jobs={filteredJobs} selectedJob={selectedJob} />
        <JobDetailDrawer job={selectedJob} />
      </div>
    </div>
  );
}

function FilterPanel({
  query,
  priority,
  companies,
  companyId,
}: {
  query: string;
  priority: string;
  companies: Array<{ id: number; name: string }>;
  companyId: number;
}) {
  return (
    <section className="rounded-lg border border-[var(--line)] bg-[var(--bg-raised)]">
      <form action="/jobs" className="grid gap-3 p-4 md:grid-cols-[minmax(0,1fr)_180px_200px_auto]">
        <label className="block">
          <span className="text-xs font-medium text-[var(--muted)]">Search</span>
          <Input name="q" defaultValue={query} placeholder="Title, company, skill" />
        </label>
        <label className="block">
          <span className="text-xs font-medium text-[var(--muted)]">Priority</span>
          <Select name="priority" defaultValue={priority}>
            <option value="">All</option>
            <option value="apply_now">Apply now</option>
            <option value="consider">Consider</option>
            <option value="stretch">Stretch</option>
            <option value="ignore">Ignore</option>
          </Select>
        </label>
        <label className="block">
          <span className="text-xs font-medium text-[var(--muted)]">Company</span>
          <Select name="company" defaultValue={Number.isInteger(companyId) ? String(companyId) : ""}>
            <option value="">All companies</option>
            {companies.map((company) => (
              <option key={company.id} value={company.id}>{company.name}</option>
            ))}
          </Select>
        </label>
        <div className="flex items-end justify-end gap-2">
          <ButtonLink href="/jobs" variant="ghost">Reset</ButtonLink>
          <Button type="submit" variant="primary">Filter</Button>
        </div>
      </form>
    </section>
  );
}

function JobsReviewList({
  jobs,
  selectedJob,
}: {
  jobs: JobRecord[];
  selectedJob?: JobRecord;
}) {
  return (
    <section className="min-w-0 overflow-hidden rounded-lg border border-[var(--line)] bg-[var(--bg-raised)]">
      <div className="flex items-center justify-between border-b border-[var(--line)] px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold text-[var(--ink)]">Matched roles</h2>
          <p className="mt-1 text-xs text-[var(--muted)]">Sorted by notification decision, score, and confidence.</p>
        </div>
        <StatusBadge tone="neutral">{jobs.length} roles</StatusBadge>
      </div>
      {jobs.length === 0 ? (
        <div className="px-4 py-8 text-sm text-[var(--muted)]">No jobs match the current filters.</div>
      ) : (
        <div className="divide-y divide-[var(--border)]">
          {jobs.map((job) => {
            const selected = job.id === selectedJob?.id;
            return (
              <Link
                key={job.id}
                href={`/jobs?job_id=${job.id}`}
                className={[
                  "block border-l-2 px-4 py-4 transition hover:bg-[var(--surface-hover)]",
                  selected ? "border-[var(--accent)] bg-[var(--accent-soft)]" : "border-transparent",
                ].join(" ")}
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="truncate text-base font-semibold text-[var(--ink)]">{job.title}</div>
                    <div className="mt-1 text-sm text-[var(--muted)]">
                      {job.company_name} · {job.location || "Location unknown"} · {labelize(job.remote_policy)}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusBadge tone={job.match.should_notify ? "success" : "neutral"}>{job.match.should_notify ? "Notify" : "Hold"}</StatusBadge>
                    <PriorityBadge priority={job.match.apply_priority} />
                    <span className="rounded border border-[var(--line)] bg-[var(--bg-sunken)] px-2 py-1 font-mono text-xs text-[var(--ink)]">
                      {job.match.overall_score}%
                    </span>
                  </div>
                </div>
                <div className="mt-3 grid gap-2 sm:grid-cols-5">
                  <ScoreCell label="Title" value={job.match.title_score} />
                  <ScoreCell label="Skills" value={job.match.skill_score} />
                  <ScoreCell label="Seniority" value={job.match.seniority_score} />
                  <ScoreCell label="Location" value={job.match.location_score} />
                  <ScoreCell label="Confidence" value={job.match.confidence_score} />
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </section>
  );
}

function JobDetailDrawer({ job }: { job?: JobRecord }) {
  if (!job) {
    return (
      <DetailDrawer title="No role selected" subtitle="Choose a job from the review list.">
        <p className="text-sm leading-6 text-[var(--muted)]">
          Match evidence, missing skills, source details, and feedback controls will appear here.
        </p>
      </DetailDrawer>
    );
  }

  return (
    <DetailDrawer
      eyebrow={`Jobs / ${job.company_name}`}
      title={job.title}
      subtitle={`${job.location || "Location unknown"} · ${labelize(job.remote_policy)}`}
      closeHref="/jobs"
      footer={
        <ButtonLink href={job.apply_url} target="_blank" variant="primary">
          Open apply link
        </ButtonLink>
      }
    >
      <div className="space-y-5">
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge tone={job.match.should_notify ? "success" : "neutral"} withDot>
            {job.match.should_notify ? "Selected for notification" : `Threshold ${job.match.notification_threshold}%`}
          </StatusBadge>
          <PriorityBadge priority={job.match.apply_priority} />
          <StatusBadge tone={job.match.confidence_score < 50 ? "warning" : "success"} withDot>
            {job.match.confidence_score}% confidence
          </StatusBadge>
        </div>

        <section className="rounded-lg border border-[var(--line)] bg-[var(--bg-sunken)] p-4">
          <div className="console-label">Agent summary</div>
          <p className="mt-3 text-sm leading-6 text-[var(--ink)]">{job.match.agent_summary || "No agent summary recorded."}</p>
        </section>

        <div className="grid gap-3 sm:grid-cols-2">
          <MatchStat label="Overall" value={job.match.overall_score} />
          <MatchStat label="Knowledge" value={job.match.knowledge_coverage_score} />
          <MatchStat label="Title" value={job.match.title_score} />
          <MatchStat label="Skills" value={job.match.skill_score} />
        </div>

        <ReasonPanel title="Reasons to apply" items={job.match.reasons_to_apply} empty="No positive evidence recorded." />
        <ReasonPanel title="Reasons to check" items={job.match.reasons_to_skip} empty="No blockers recorded." />

        {job.match.missing_skills.length ? (
          <section className="rounded-lg border border-[var(--warn)] bg-[var(--warn-soft)] p-4">
            <div className="console-label">Missing or weak skills</div>
            <div className="mt-3 flex flex-wrap gap-2">
              {job.match.missing_skills.map((skill) => (
                <span key={skill} className="rounded border border-[var(--line)] bg-[var(--bg)] px-2 py-1 text-xs font-medium text-[var(--ink)]">
                  {skill}
                </span>
              ))}
            </div>
          </section>
        ) : null}

        <FeedbackPanel job={job} />
        <EvidencePanel evidence={job.match.evidence} />

        <section className="rounded-lg border border-[var(--line)] bg-[var(--bg-sunken)] p-4">
          <div className="console-label">Description extract</div>
          <p className="mt-3 max-h-72 overflow-auto whitespace-pre-wrap text-sm leading-6 text-[var(--muted)]">
            {job.description || "No description recorded."}
          </p>
        </section>
      </div>
    </DetailDrawer>
  );
}

function FeedbackPanel({ job }: { job: JobRecord }) {
  const options = [
    ["good_match", "Good match"],
    ["bad_match", "Bad match"],
    ["too_senior", "Too senior"],
    ["too_junior", "Too junior"],
    ["wrong_location", "Wrong location"],
    ["wrong_role", "Wrong role"],
    ["too_many_notifications", "Too many"],
    ["want_more_matches", "More like this"],
  ];

  return (
    <section className="rounded-lg border border-[var(--line)] bg-[var(--bg-raised)] p-4">
      <div className="console-label">Tune future matches</div>
      <form action={submitJobFeedbackAction} className="mt-3 space-y-3">
        <input type="hidden" name="job_id" value={job.id} />
        <Select name="feedback_type" defaultValue="good_match">
          {options.map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </Select>
        <Textarea name="notes" rows={3} placeholder="Optional note for why this match is right or wrong." />
        <Button type="submit" variant="primary">Save feedback</Button>
      </form>
    </section>
  );
}

function PriorityBadge({ priority }: { priority: string }) {
  const tone = priority === "apply_now" ? "success" : priority === "consider" ? "info" : priority === "stretch" ? "warning" : "neutral";
  return <StatusBadge tone={tone}>{labelize(priority)}</StatusBadge>;
}

function ScoreCell({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded border border-[var(--line)] bg-[var(--bg-sunken)] p-2">
      <div className="font-mono text-[10px] uppercase tracking-[0.12em] text-[var(--faint)]">{label}</div>
      <div className="mt-1 font-mono text-xs font-semibold text-[var(--ink)]">{value}%</div>
    </div>
  );
}

function MatchStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-[var(--line)] bg-[var(--bg-sunken)] p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <span className="text-sm font-medium text-[var(--muted)]">{label}</span>
        <span className="font-mono text-sm font-semibold text-[var(--ink)]">{value}%</span>
      </div>
      <ScoreBar value={value} />
    </div>
  );
}

function ReasonPanel({ title, items, empty }: { title: string; items: string[]; empty: string }) {
  return (
    <section className="rounded-lg border border-[var(--line)] bg-[var(--bg-raised)] p-4">
      <div className="console-label">{title}</div>
      {items.length === 0 ? (
        <p className="mt-3 text-sm text-[var(--muted)]">{empty}</p>
      ) : (
        <ul className="mt-3 space-y-2 text-sm leading-6 text-[var(--ink)]">
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}
    </section>
  );
}

function EvidencePanel({ evidence }: { evidence: Array<Record<string, unknown>> }) {
  if (!evidence.length) return null;
  return (
    <section className="rounded-lg border border-[var(--line)] bg-[var(--bg-raised)] p-4">
      <div className="console-label">Evidence</div>
      <div className="mt-3 space-y-3">
        {evidence.map((item, index) => (
          <div key={index} className="rounded border border-[var(--line)] bg-[var(--bg-sunken)] p-3">
            <div className="font-mono text-[11px] text-[var(--accent)]">{String(item.kind || "evidence")}</div>
            <div className="mt-1 text-sm text-[var(--ink)]">{String(item.message || "")}</div>
            {Array.isArray(item.values) && item.values.length ? (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {item.values.map((value) => (
                  <span key={String(value)} className="rounded bg-[var(--bg)] px-1.5 py-1 font-mono text-[10px] text-[var(--muted)]">
                    {String(value)}
                  </span>
                ))}
              </div>
            ) : null}
          </div>
        ))}
      </div>
    </section>
  );
}

function labelize(value: string) {
  return value.replace(/_/g, " ");
}

function getSearchParam(
  params: Record<string, string | string[] | undefined>,
  key: string,
) {
  const value = params[key];
  return Array.isArray(value) ? value[0] : value || "";
}
