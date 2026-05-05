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
import { getApiErrorMessage, listJobs, listManualUrlInbox, toApiResult } from "@/lib/api";
import type { JobMatchEvidence, JobRecord, ManualUrlInboxItem, MatchApplyPriority } from "@/lib/api";
import {
  addManualUrlAction,
  dismissManualUrlAction,
  importManualUrlAction,
  saveJobAsApplicationAction,
  skipJobAsApplicationAction,
} from "./actions";

type JobsPageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function JobsPage({ searchParams }: JobsPageProps) {
  const params = await searchParams;
  const query = getSearchParam(params, "q");
  const remote = getSearchParam(params, "remote");
  const priority = getSearchParam(params, "priority");
  const notice = getSearchParam(params, "jobs_notice");
  const error = getSearchParam(params, "jobs_error");
  const selectedJobId = Number(getSearchParam(params, "job_id"));
  const jobsResult = await toApiResult(
    listJobs({
      q: query,
      remote,
      country: "all",
      strong_fit_first: true,
    }),
  );
  const inboxResult = await toApiResult(listManualUrlInbox("pending"));
  const jobs = jobsResult.ok ? jobsResult.data.results : [];
  const inboxItems = inboxResult.ok ? inboxResult.data.results : [];
  const filteredJobs = priority ? jobs.filter((job) => job.match.apply_priority === priority) : jobs;
  const selectedJob =
    (Number.isInteger(selectedJobId)
      ? filteredJobs.find((job) => job.id === selectedJobId)
      : undefined) ?? filteredJobs[0];
  const applyNowCount = jobs.filter((job) => job.match.apply_priority === "apply_now").length;
  const considerCount = jobs.filter((job) => job.match.apply_priority === "consider").length;
  const lowConfidenceCount = jobs.filter((job) => job.match.confidence_score < 50).length;

  return (
    <div className="space-y-4">
      <PageHeader
        title="Jobs"
        eyebrow="Discovery review"
        description="Strong-fit-first role review with match evidence, missing skills, and direct save or skip decisions."
        actions={
          <StatusBadge tone="info" withDot>
            Deterministic ranking
          </StatusBadge>
        }
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
      {!inboxResult.ok ? (
        <ErrorState
          title="Discovery inbox is unavailable"
          message="Manual URLs could not be loaded."
          detail={getApiErrorMessage(inboxResult.error)}
        />
      ) : null}

      <div className="grid gap-3 md:grid-cols-4">
        <MetricCard label="Jobs" value={jobs.length} detail="Discovered roles" />
        <MetricCard label="Apply now" value={applyNowCount} detail="Strongest fit" />
        <MetricCard label="Consider" value={considerCount} detail="Worth review" />
        <MetricCard label="Low confidence" value={lowConfidenceCount} detail="Improve profile" />
      </div>

      <FilterPanel query={query} remote={remote} priority={priority} />

      <div className="grid min-w-0 gap-4 xl:grid-cols-[minmax(0,1fr)_500px]">
        <JobsReviewList jobs={filteredJobs} selectedJob={selectedJob} />
        <JobDetailDrawer job={selectedJob} />
      </div>

      <ManualUrlInboxPanel items={inboxItems} />
    </div>
  );
}

function FilterPanel({
  query,
  remote,
  priority,
}: {
  query: string;
  remote: string;
  priority: string;
}) {
  return (
    <section className="rounded-lg border border-slate-800 bg-slate-900">
      <form action="/jobs" className="grid gap-3 p-4 md:grid-cols-[minmax(0,1fr)_180px_180px_auto]">
        <label className="block">
          <span className="text-xs font-medium text-slate-500">Search</span>
          <Input name="q" defaultValue={query} placeholder="Title, company, skill" />
        </label>
        <label className="block">
          <span className="text-xs font-medium text-slate-500">Work mode</span>
          <Select name="remote" defaultValue={remote}>
            <option value="">Any</option>
            <option value="remote">Remote</option>
            <option value="hybrid">Hybrid</option>
            <option value="onsite">Onsite</option>
          </Select>
        </label>
        <label className="block">
          <span className="text-xs font-medium text-slate-500">Priority</span>
          <Select name="priority" defaultValue={priority}>
            <option value="">All</option>
            <option value="apply_now">Apply now</option>
            <option value="consider">Consider</option>
            <option value="stretch">Stretch</option>
            <option value="ignore">Ignore</option>
          </Select>
        </label>
        <div className="flex items-end justify-end gap-2">
          <ButtonLink href="/jobs" variant="ghost">
            Reset
          </ButtonLink>
          <Button type="submit" variant="primary">
            Filter
          </Button>
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
    <section className="min-w-0 overflow-hidden rounded-lg border border-slate-800 bg-slate-900">
      <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold text-slate-50">Strong-fit-first roles</h2>
          <p className="mt-1 text-xs text-slate-500">Select a role to inspect evidence and decide.</p>
        </div>
        <StatusBadge tone="neutral">{jobs.length} roles</StatusBadge>
      </div>
      {jobs.length === 0 ? (
        <div className="px-4 py-8 text-sm text-slate-500">No jobs match the current filters.</div>
      ) : (
        <div className="divide-y divide-slate-800">
          {jobs.map((job) => {
            const selected = job.id === selectedJob?.id;
            return (
              <Link
                key={job.id}
                href={`/jobs?job_id=${job.id}`}
                className={[
                  "block border-l-2 px-4 py-4 transition hover:bg-slate-800",
                  selected ? "border-indigo-300 bg-indigo-500/10" : "border-transparent",
                ].join(" ")}
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="truncate text-base font-semibold text-slate-50">{job.title}</div>
                    <div className="mt-1 text-sm text-slate-500">
                      {job.company} - {job.location || "Location unknown"} - {labelize(job.remote_policy)}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <PriorityBadge priority={job.match.apply_priority} />
                    <span className="rounded border border-slate-700 bg-slate-950 px-2 py-1 font-mono text-xs text-slate-200">
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
        <p className="text-sm leading-6 text-slate-500">
          Match evidence, missing skills, source description, and application actions will appear here.
        </p>
      </DetailDrawer>
    );
  }

  return (
    <DetailDrawer
      eyebrow={`Jobs / ${job.company}`}
      title={job.title}
      subtitle={`${job.location || "Location unknown"} - ${labelize(job.remote_policy)}`}
      closeHref="/jobs"
      footer={
        <div className="grid gap-2 sm:grid-cols-3 xl:grid-cols-1">
          <form action={saveJobAsApplicationAction}>
            <input type="hidden" name="job_id" value={job.id} />
            <Button type="submit" variant="primary" className="w-full">
              Save Application
            </Button>
          </form>
          <form action={skipJobAsApplicationAction}>
            <input type="hidden" name="job_id" value={job.id} />
            <Button type="submit" variant="default" className="w-full">
              Skip
            </Button>
          </form>
          <ButtonLink href={job.apply_url} target="_blank" variant="default">
            Open Original
          </ButtonLink>
        </div>
      }
    >
      <div className="space-y-5">
        <div className="flex flex-wrap items-center gap-2">
          <PriorityBadge priority={job.match.apply_priority} />
          <StatusBadge tone={job.match.confidence_score < 50 ? "warning" : "success"} withDot>
            {job.match.confidence_score}% confidence
          </StatusBadge>
          <StatusBadge tone="neutral">{job.match.source}</StatusBadge>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <MatchStat label="Overall" value={job.match.overall_score} />
          <MatchStat label="Knowledge" value={job.match.knowledge_coverage_score} />
          <MatchStat label="Title" value={job.match.title_score} />
          <MatchStat label="Skills" value={job.match.skill_score} />
        </div>

        <ReasonPanel title="Reasons to apply" items={job.match.reasons_to_apply} empty="No positive evidence recorded." />
        <ReasonPanel title="Reasons to check" items={job.match.reasons_to_skip} empty="No blockers recorded." />

        {job.match.missing_skills.length ? (
          <section className="rounded-lg border border-amber-400/30 bg-amber-400/10 p-4">
            <div className="console-label">Missing or weak skills</div>
            <div className="mt-3 flex flex-wrap gap-2">
              {job.match.missing_skills.map((skill) => (
                <span key={skill} className="rounded border border-amber-400/30 bg-amber-400/10 px-2 py-1 text-xs font-medium text-amber-200">
                  {skill}
                </span>
              ))}
            </div>
          </section>
        ) : null}

        <EvidencePanel evidence={job.match.evidence} />

        <section className="rounded-lg border border-slate-800 bg-slate-950 p-4">
          <div className="console-label">Description extract</div>
          <p className="mt-3 max-h-72 overflow-auto whitespace-pre-wrap text-sm leading-6 text-slate-300">
            {job.description || "No description recorded."}
          </p>
        </section>
      </div>
    </DetailDrawer>
  );
}

function ManualUrlInboxPanel({ items }: { items: ManualUrlInboxItem[] }) {
  return (
    <section className="rounded-lg border border-slate-800 bg-slate-900">
      <div className="border-b border-slate-800 px-4 py-3">
        <h2 className="text-sm font-semibold text-slate-50">Manual URL inbox</h2>
      </div>
      <div className="grid gap-4 p-4 xl:grid-cols-[420px_minmax(0,1fr)]">
        <form action={addManualUrlAction} className="space-y-3">
          <label className="block">
            <span className="text-xs font-medium text-slate-500">URL</span>
            <Input name="url" placeholder="https://company.com/careers" />
          </label>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block">
              <span className="text-xs font-medium text-slate-500">Type</span>
              <Select name="item_type" defaultValue="unknown">
                <option value="unknown">Auto</option>
                <option value="company">Company</option>
                <option value="job">Job</option>
              </Select>
            </label>
            <label className="block">
              <span className="text-xs font-medium text-slate-500">Title</span>
              <Input name="title" />
            </label>
          </div>
          <label className="block">
            <span className="text-xs font-medium text-slate-500">Notes</span>
            <Textarea name="notes" rows={3} />
          </label>
          <Button type="submit" variant="primary">
            Add URL
          </Button>
        </form>
        <div className="rounded-md border border-slate-800">
          {items.length === 0 ? (
            <div className="px-4 py-5 text-sm text-slate-500">No pending manual URLs.</div>
          ) : (
            <div className="divide-y divide-slate-800">
              {items.map((item) => (
                <article key={item.id} className="px-4 py-3">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="text-sm font-semibold text-slate-50">{item.title || item.inferred_company || item.url}</div>
                      <Link href={item.url} target="_blank" className="mt-1 block truncate text-xs text-cyan-300 hover:text-cyan-200">
                        {item.url}
                      </Link>
                      <div className="mt-2 flex flex-wrap gap-2">
                        <StatusBadge tone="neutral">{item.item_type}</StatusBadge>
                        <StatusBadge tone="warning" withDot>{item.status}</StatusBadge>
                      </div>
                    </div>
                    <div className="flex shrink-0 gap-2">
                      <ManualUrlButton itemId={item.id} action={importManualUrlAction} label="Import" />
                      <ManualUrlButton itemId={item.id} action={dismissManualUrlAction} label="Dismiss" />
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

function ManualUrlButton({
  itemId,
  action,
  label,
}: {
  itemId: number;
  action: (formData: FormData) => Promise<void>;
  label: string;
}) {
  return (
    <form action={action}>
      <input type="hidden" name="item_id" value={itemId} />
      <Button type="submit" size="sm">
        {label}
      </Button>
    </form>
  );
}

function EvidencePanel({ evidence }: { evidence: JobMatchEvidence[] }) {
  return (
    <section className="rounded-lg border border-slate-800 bg-slate-950 p-4">
      <div className="console-label">Match evidence</div>
      {evidence.length === 0 ? (
        <p className="mt-3 text-sm text-slate-500">No evidence recorded yet.</p>
      ) : (
        <div className="mt-3 space-y-3">
          {evidence.map((item, index) => (
            <div key={`${item.kind}-${index}`} className="rounded-md border border-slate-800 bg-slate-900 px-3 py-2">
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge tone="neutral">{labelize(item.kind)}</StatusBadge>
                <span className="text-xs font-medium text-slate-300">{item.message}</span>
              </div>
              {item.values.length ? (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {item.values.map((value) => (
                    <span key={value} className="rounded bg-slate-800 px-2 py-1 text-xs text-slate-400">
                      {value}
                    </span>
                  ))}
                </div>
              ) : null}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function ReasonPanel({ title, items, empty }: { title: string; items: string[]; empty: string }) {
  return (
    <section className="rounded-lg border border-slate-800 bg-slate-950 p-4">
      <div className="console-label">{title}</div>
      {items.length ? (
        <ul className="mt-3 space-y-2 text-sm leading-6 text-slate-300">
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-sm text-slate-500">{empty}</p>
      )}
    </section>
  );
}

function MatchStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border border-slate-800 bg-slate-950 px-3 py-2">
      <div className="console-label">{label}</div>
      <div className="mt-2 flex items-center justify-between gap-3">
        <div className="font-mono text-lg font-semibold text-slate-100">{value}</div>
        <div className="font-mono text-[10px] text-slate-500">/100</div>
      </div>
      <ScoreBar value={value} className="mt-2" />
    </div>
  );
}

function ScoreCell({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border border-slate-800 bg-slate-950 px-3 py-2">
      <div className="font-mono text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-600">{label}</div>
      <div className="mt-1 flex items-center justify-between gap-2">
        <div className="font-mono text-xs font-semibold text-slate-300">{value}</div>
        <div className="font-mono text-[10px] text-slate-600">/100</div>
      </div>
      <ScoreBar value={value} className="mt-2" />
    </div>
  );
}

function PriorityBadge({ priority }: { priority: MatchApplyPriority }) {
  const tone = priority === "apply_now" ? "success" : priority === "consider" ? "info" : priority === "stretch" ? "warning" : "neutral";
  return (
    <StatusBadge tone={tone} withDot>
      {labelize(priority)}
    </StatusBadge>
  );
}

function labelize(value: string) {
  if (!value) {
    return "Unknown";
  }

  return value
    .replaceAll("_", " ")
    .split(" ")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function getSearchParam(params: Record<string, string | string[] | undefined>, key: string) {
  const value = params[key];
  return Array.isArray(value) ? value[0] ?? "" : value ?? "";
}
