import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";
import { Input } from "@/components/ui/form-controls";
import { MetricCard } from "@/components/ui/metric-card";
import { PageHeader } from "@/components/ui/page-header";
import { PageSection } from "@/components/ui/page-section";
import { StatusBadge } from "@/components/ui/status-badge";
import { SystemBanner } from "@/components/ui/system-banner";
import { getAnalyticsOverview, getApiErrorMessage, toApiResult } from "@/lib/api";
import type {
  AlertFeedback,
  AnalyticsSignal,
  CompanyQualityMetric,
  FeedbackCandidate,
  FilterSuggestion,
  PlatformQualityMetric,
  WeeklyReview,
} from "@/lib/api";
import { generateWeeklyReviewAction, markAlertUsefulnessAction } from "./actions";

type AnalyticsPageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function AnalyticsPage({ searchParams }: AnalyticsPageProps) {
  const params = await searchParams;
  const notice = getSearchParam(params, "analytics_notice");
  const error = getSearchParam(params, "analytics_error");
  const overviewResult = await toApiResult(getAnalyticsOverview(12));
  const overview = overviewResult.ok ? overviewResult.data : null;

  return (
    <div className="space-y-4">
      <PageHeader
        title="Analytics"
        eyebrow="Learning"
        description="Source quality, alert usefulness, noisy signals, and review-only filter suggestions."
        actions={
          <div className="flex flex-wrap items-center justify-end gap-2">
            {overview ? (
              <StatusBadge tone={overview.summary.suggestions_total ? "warning" : "success"} withDot>
                {overview.summary.suggestions_total} suggestions
              </StatusBadge>
            ) : null}
            <form action={generateWeeklyReviewAction}>
              <Button type="submit" variant="primary">
                Weekly review
              </Button>
            </form>
          </div>
        }
      />

      {notice ? (
        <SystemBanner tone="success">
          {notice}
        </SystemBanner>
      ) : null}

      {error ? <ErrorState title="Analytics action failed" message={error} /> : null}

      {!overviewResult.ok ? (
        <ErrorState
          title="Backend API is unavailable"
          message="Analytics could not be loaded."
          detail={getApiErrorMessage(overviewResult.error)}
        />
      ) : null}

      {overview ? (
        <>
          <div className="grid gap-3 md:grid-cols-4">
            <MetricCard label="Tracked" value={overview.summary.companies_tracked} detail="Companies" />
            <MetricCard label="Alerts" value={overview.summary.alerts_total} detail="Role signals" />
            <MetricCard label="Feedback" value={overview.summary.feedback_total} detail={`${overview.summary.feedback_relevant} relevant`} />
            <MetricCard label="Failing" value={overview.summary.sources_failing} detail="Sources" />
          </div>

          <WeeklyReviewPanel review={overview.latest_weekly_review} />

          <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
            <CompanyQualityPanel metrics={overview.company_metrics} />
            <FeedbackInboxPanel candidates={overview.feedback_inbox} />
          </div>

          <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
            <PlatformQualityPanel metrics={overview.platform_metrics} />
            <SignalsPanel signals={overview.noisy_signals} suggestions={overview.filter_suggestions} />
          </div>

          <RecentFeedbackPanel feedback={overview.recent_feedback} />
        </>
      ) : null}
    </div>
  );
}

function WeeklyReviewPanel({ review }: { review: WeeklyReview | null }) {
  return (
    <PageSection
      title="Weekly review"
      actions={review?.period_end ? <StatusBadge tone="info">{formatDate(review.period_end)}</StatusBadge> : null}
    >
      {!review ? (
        <div className="px-4 py-5 text-sm text-slate-600">No weekly review generated yet.</div>
      ) : (
        <div className="grid gap-4 p-4 lg:grid-cols-3">
          <div className="text-sm leading-6 text-slate-700 lg:col-span-3">{review.summary}</div>
          <ReviewList title="Recommendations" items={review.recommendations} empty="No recommendations." />
          <ReviewList title="Risks" items={review.risks} empty="No risks." />
          <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
            <h3 className="text-xs font-semibold uppercase tracking-normal text-slate-500">Snapshot</h3>
            <pre className="mt-2 max-h-40 overflow-auto text-xs leading-5 text-slate-700">
              {JSON.stringify(review.metrics_snapshot.summary ?? review.metrics_snapshot, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </PageSection>
  );
}

function ReviewList({
  title,
  items,
  empty,
}: {
  title: string;
  items: Array<Record<string, unknown>>;
  empty: string;
}) {
  return (
    <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
      <h3 className="text-xs font-semibold uppercase tracking-normal text-slate-500">{title}</h3>
      {items.length ? (
        <ul className="mt-2 space-y-2 text-sm leading-5 text-slate-700">
          {items.map((item, index) => (
            <li key={`${String(item.kind ?? title)}-${index}`}>
              {String(item.message ?? item.kind ?? "Review item")}
              {typeof item.count === "number" ? <span className="text-slate-500"> ({item.count})</span> : null}
            </li>
          ))}
        </ul>
      ) : (
        <div className="mt-2 text-sm text-slate-600">{empty}</div>
      )}
    </div>
  );
}

function CompanyQualityPanel({ metrics }: { metrics: CompanyQualityMetric[] }) {
  const sortedMetrics = [...metrics].sort((a, b) => {
    const aScore = a.usefulness_score ?? -1;
    const bScore = b.usefulness_score ?? -1;
    if (a.noisy !== b.noisy) return a.noisy ? -1 : 1;
    return bScore - aScore;
  });

  return (
    <section className="rounded-lg border border-slate-200 bg-white">
      <div className="border-b border-slate-200 px-4 py-3">
        <h2 className="text-sm font-semibold text-slate-950">Company source quality</h2>
      </div>
      {sortedMetrics.length === 0 ? (
        <div className="px-4 py-5 text-sm text-slate-600">No company data yet.</div>
      ) : (
        <div className="divide-y divide-slate-100">
          {sortedMetrics.slice(0, 20).map((metric) => (
            <article key={metric.company_id} className="px-4 py-3">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <Link href={`/companies`} className="text-sm font-semibold text-slate-950 hover:text-cyan-700">
                    {metric.company_name}
                  </Link>
                  <div className="mt-1 flex flex-wrap gap-2">
                    <StatusBadge tone={sourceTone(metric.source_health)} withDot>
                      {labelize(metric.source_health)}
                    </StatusBadge>
                    <StatusBadge tone={metric.noisy ? "warning" : "neutral"}>
                      {metric.noisy ? "Noisy" : metric.source_platform}
                    </StatusBadge>
                    {metric.stale ? <StatusBadge tone="warning">Stale</StatusBadge> : null}
                  </div>
                </div>
                <div className="text-right text-xs text-slate-500">
                  <div className="font-semibold text-slate-950">{formatScore(metric.usefulness_score)}</div>
                  <div>Usefulness</div>
                </div>
              </div>
              <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-4">
                <SignalStat label="Scans" value={`${metric.successful_scans}/${metric.scan_count}`} />
                <SignalStat label="Alerts" value={metric.alerts_total} />
                <SignalStat label="Apps" value={metric.applications_total} />
                <SignalStat
                  label="Feedback"
                  value={`${metric.feedback_relevant}/${metric.feedback_maybe}/${metric.feedback_irrelevant}`}
                />
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function FeedbackInboxPanel({ candidates }: { candidates: FeedbackCandidate[] }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white">
      <div className="border-b border-slate-200 px-4 py-3">
        <h2 className="text-sm font-semibold text-slate-950">Feedback inbox</h2>
      </div>
      {candidates.length === 0 ? (
        <div className="px-4 py-5 text-sm text-slate-600">No unlabeled alerts.</div>
      ) : (
        <div className="divide-y divide-slate-100">
          {candidates.map((candidate) => (
            <article key={candidate.alert_id} className="space-y-3 px-4 py-3">
              <div>
                <Link href={candidate.apply_url} target="_blank" className="text-sm font-semibold text-slate-950 hover:text-cyan-700">
                  {candidate.job_title}
                </Link>
                <div className="mt-1 text-xs text-slate-500">
                  {candidate.company_name} · {candidate.location || "Location unknown"} · {formatDate(candidate.created_at)}
                </div>
              </div>
              <form action={markAlertUsefulnessAction} className="space-y-2">
                <input type="hidden" name="alert_id" value={candidate.alert_id} />
                <div className="grid grid-cols-3 gap-2">
                  <FeedbackButton rating="relevant" />
                  <FeedbackButton rating="maybe" />
                  <FeedbackButton rating="irrelevant" />
                </div>
                <Input
                  name="reason"
                  placeholder="Reason"
                  className="mt-0 h-8 text-xs"
                />
                <Input
                  name="tags"
                  placeholder="Tags"
                  className="mt-0 h-8 text-xs"
                />
              </form>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function FeedbackButton({ rating }: { rating: "relevant" | "maybe" | "irrelevant" }) {
  return (
    <button
      type="submit"
      name="rating"
      value={rating}
      className={[
        "h-8 rounded-md border px-2 text-xs font-semibold transition",
        rating === "relevant"
          ? "border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100"
          : rating === "maybe"
            ? "border-amber-200 bg-amber-50 text-amber-800 hover:bg-amber-100"
            : "border-rose-200 bg-rose-50 text-rose-700 hover:bg-rose-100",
      ].join(" ")}
    >
      {labelize(rating)}
    </button>
  );
}

function PlatformQualityPanel({ metrics }: { metrics: PlatformQualityMetric[] }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white">
      <div className="border-b border-slate-200 px-4 py-3">
        <h2 className="text-sm font-semibold text-slate-950">Platform quality</h2>
      </div>
      {metrics.length === 0 ? (
        <div className="px-4 py-5 text-sm text-slate-600">No platform metrics yet.</div>
      ) : (
        <div className="divide-y divide-slate-100">
          {metrics.map((metric) => (
            <div key={metric.source_platform} className="grid gap-3 px-4 py-3 md:grid-cols-[160px_minmax(0,1fr)]">
              <div>
                <div className="text-sm font-semibold text-slate-950">{labelize(metric.source_platform)}</div>
                <div className="mt-1 text-xs text-slate-500">{metric.active_companies}/{metric.companies_total} active</div>
              </div>
              <div className="grid gap-2 text-xs text-slate-600 sm:grid-cols-4">
                <SignalStat label="Scan success" value={formatPercent(metric.success_rate)} />
                <SignalStat label="Alerts" value={metric.alerts_total} />
                <SignalStat label="Feedback" value={metric.feedback_total} />
                <SignalStat label="Usefulness" value={formatScore(metric.usefulness_score)} />
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function SignalsPanel({
  signals,
  suggestions,
}: {
  signals: AnalyticsSignal[];
  suggestions: FilterSuggestion[];
}) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white">
      <div className="border-b border-slate-200 px-4 py-3">
        <h2 className="text-sm font-semibold text-slate-950">Review signals</h2>
      </div>
      {signals.length === 0 && suggestions.length === 0 ? (
        <div className="px-4 py-5 text-sm text-slate-600">No noisy signals or filter suggestions yet.</div>
      ) : (
        <div className="divide-y divide-slate-100">
          {signals.map((signal, index) => (
            <article key={`${signal.kind}-${signal.company_id}-${index}`} className="px-4 py-3">
              <div className="flex items-center justify-between gap-3">
                <h3 className="text-sm font-semibold text-slate-950">{signal.company_name}</h3>
                <StatusBadge tone="warning">{labelize(signal.kind)}</StatusBadge>
              </div>
              <p className="mt-1 text-sm leading-6 text-slate-600">{signal.message}</p>
            </article>
          ))}
          {suggestions.map((suggestion, index) => (
            <article key={`${suggestion.suggestion_type}-${suggestion.company_id}-${index}`} className="px-4 py-3">
              <div className="flex items-center justify-between gap-3">
                <h3 className="text-sm font-semibold text-slate-950">{suggestion.company_name}</h3>
                <StatusBadge tone="info">{labelize(suggestion.suggestion_type)}</StatusBadge>
              </div>
              <p className="mt-1 text-sm leading-6 text-slate-600">{suggestion.message}</p>
              {suggestion.evidence.length ? (
                <ul className="mt-2 space-y-1 text-xs text-slate-500">
                  {suggestion.evidence.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              ) : null}
              {suggestion.requires_review ? (
                <div className="mt-2 text-xs font-medium text-slate-500">Review required before filters change.</div>
              ) : null}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function RecentFeedbackPanel({ feedback }: { feedback: AlertFeedback[] }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white">
      <div className="border-b border-slate-200 px-4 py-3">
        <h2 className="text-sm font-semibold text-slate-950">Recent feedback</h2>
      </div>
      {feedback.length === 0 ? (
        <div className="px-4 py-5 text-sm text-slate-600">No feedback recorded yet.</div>
      ) : (
        <div className="divide-y divide-slate-100">
          {feedback.map((item) => (
            <div key={item.id} className="grid gap-2 px-4 py-3 md:grid-cols-[160px_minmax(0,1fr)_auto]">
              <div className="text-sm font-semibold text-slate-950">{item.company_name}</div>
              <div>
                <div className="text-sm text-slate-800">{item.job_title}</div>
                <div className="mt-1 text-xs text-slate-500">{item.reason || "No reason recorded"}</div>
              </div>
              <div className="flex items-start justify-end">
                <StatusBadge tone={feedbackTone(item.rating)}>{labelize(item.rating)}</StatusBadge>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function SignalStat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
      <div className="text-[11px] font-medium uppercase tracking-normal text-slate-500">{label}</div>
      <div className="mt-1 text-sm font-semibold text-slate-950">{value}</div>
    </div>
  );
}

function getSearchParam(params: Record<string, string | string[] | undefined>, key: string) {
  const value = params[key];
  return Array.isArray(value) ? value[0] : value;
}

function labelize(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatPercent(value: number | null) {
  return value === null ? "n/a" : `${Math.round(value * 100)}%`;
}

function formatScore(value: number | null) {
  return value === null ? "n/a" : `${value}/100`;
}

function formatDate(value: string | null) {
  if (!value) {
    return "Not recorded";
  }

  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
  }).format(new Date(value));
}

function sourceTone(sourceHealth: string) {
  if (sourceHealth === "active") return "success";
  if (sourceHealth === "degraded" || sourceHealth === "needs_setup") return "warning";
  if (sourceHealth === "failing" || sourceHealth === "blocked") return "danger";
  return "neutral";
}

function feedbackTone(rating: string) {
  if (rating === "relevant") return "success";
  if (rating === "maybe") return "warning";
  if (rating === "irrelevant") return "danger";
  return "neutral";
}
