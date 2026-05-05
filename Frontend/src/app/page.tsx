import Link from "next/link";
import { Button, ButtonLink } from "@/components/ui/button";
import { DetailDrawer } from "@/components/ui/detail-drawer";
import { ErrorState } from "@/components/ui/error-state";
import { Input } from "@/components/ui/form-controls";
import { MetricCard } from "@/components/ui/metric-card";
import { PageHeader } from "@/components/ui/page-header";
import { StatusBadge } from "@/components/ui/status-badge";
import { SystemBanner } from "@/components/ui/system-banner";
import {
  getApiErrorMessage,
  getBackendHealth,
  listCompanies,
  listJobAlerts,
  listScanJobs,
  listTodayActions,
  toApiResult,
} from "@/lib/api";
import type { JobAlert, ScanJob, TodayAction } from "@/lib/api";
import {
  completeTodayActionAction,
  dismissAlertAction,
  dismissTodayActionAction,
  markAlertReadAction,
  runDueScansAction,
  saveAlertAsApplicationAction,
  skipAlertAsApplicationAction,
} from "./actions";

type TodayPageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

type InboxItem =
  | { kind: "alert"; id: string; alert: JobAlert }
  | { kind: "action"; id: string; action: TodayAction };

export default async function TodayPage({ searchParams }: TodayPageProps) {
  const params = await searchParams;
  const todayNotice = getSearchParam(params, "today_notice");
  const todayError = getSearchParam(params, "today_error");
  const selectedAlertId = Number(getSearchParam(params, "alert_id"));
  const selectedActionId = Number(getSearchParam(params, "action_id"));

  const [healthResult, companiesResult, alertsResult, todayActionsResult, scanJobsResult] =
    await Promise.all([
      toApiResult(getBackendHealth()),
      toApiResult(listCompanies()),
      toApiResult(listJobAlerts({ status: "unread", limit: 12 })),
      toApiResult(listTodayActions({ status: "open", limit: 16 })),
      toApiResult(listScanJobs({ limit: 8 })),
    ]);

  const backendOnline =
    healthResult.ok && String(healthResult.data.status).toLowerCase() === "ok";
  const companies = companiesResult.ok ? companiesResult.data.results : [];
  const unreadAlerts = alertsResult.ok ? alertsResult.data.results : [];
  const todayActions = todayActionsResult.ok ? todayActionsResult.data.results : [];
  const scanJobs = scanJobsResult.ok ? scanJobsResult.data.results : [];
  const failedScans = scanJobs.filter((scanJob) => scanJob.status === "failed");
  const dueCompanies = companies.filter((company) => company.is_active && !company.last_scraped_at);
  const inboxItems: InboxItem[] = [
    ...unreadAlerts.map((alert) => ({ kind: "alert" as const, id: `alert-${alert.id}`, alert })),
    ...todayActions.map((action) => ({ kind: "action" as const, id: `action-${action.id}`, action })),
  ];
  const selectedItem =
    (Number.isInteger(selectedAlertId)
      ? inboxItems.find((item) => item.kind === "alert" && item.alert.id === selectedAlertId)
      : undefined) ??
    (Number.isInteger(selectedActionId)
      ? inboxItems.find((item) => item.kind === "action" && item.action.id === selectedActionId)
      : undefined) ??
    inboxItems[0];

  return (
    <div className="space-y-4">
      <PageHeader
        title="Today"
        eyebrow="Command center"
        description="Triage new roles, due follow-ups, scan health, and next actions without leaving the daily console."
        actions={
          <StatusBadge tone={backendOnline ? "success" : "danger"} withDot>
            {backendOnline ? "Backend online" : "Backend down"}
          </StatusBadge>
        }
      />

      {todayNotice ? <SystemBanner tone="success">{todayNotice}</SystemBanner> : null}
      {todayError ? <ErrorState title="Today action failed" message={todayError} /> : null}

      {!companiesResult.ok ? (
        <ErrorState
          title="Backend API is unavailable"
          message="Today could not load company tracking data."
          detail={getApiErrorMessage(companiesResult.error)}
        />
      ) : null}

      <div className="grid gap-3 md:grid-cols-4">
        <MetricCard label="Tracked companies" value={companies.length} detail="Watchlist size" />
        <MetricCard label="Open actions" value={todayActions.length} detail="Today queue" />
        <MetricCard label="Unread alerts" value={unreadAlerts.length} detail="New role signals" />
        <MetricCard label="Recent failures" value={failedScans.length} detail="Needs source review" />
      </div>

      <section className="rounded-lg border border-slate-800 bg-slate-900">
        <div className="flex flex-col gap-3 border-b border-slate-800 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-sm font-semibold text-slate-50">Scan control</h2>
            <p className="mt-1 text-xs text-slate-500">
              Run due active companies using each company scan cadence.
            </p>
          </div>
          <form action={runDueScansAction} className="flex items-center gap-2">
            <Input
              name="limit"
              type="number"
              min="1"
              max="100"
              defaultValue="10"
              className="mt-0 h-8 w-20 font-mono text-xs"
            />
            <Button type="submit" variant="primary" size="sm">
              Run due scans
            </Button>
          </form>
        </div>
        <div className="grid divide-y divide-slate-800 md:grid-cols-3 md:divide-x md:divide-y-0">
          <AttentionLink
            href="/companies"
            label="Companies to review"
            value={companies.filter((company) => ["failing", "blocked", "degraded"].includes(company.source_health)).length}
          />
          <AttentionLink href="/companies" label="Ready for first scan" value={dueCompanies.length} />
          <AttentionLink href="/settings" label="Scheduler command" value="Available" />
        </div>
      </section>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_480px]">
        <section className="overflow-hidden rounded-lg border border-slate-800 bg-slate-900">
          <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
            <div>
              <h2 className="text-sm font-semibold text-slate-50">Daily inbox</h2>
              <p className="mt-1 text-xs text-slate-500">
                New-role alerts and open actions are merged for fast triage.
              </p>
            </div>
            <StatusBadge tone="neutral">{inboxItems.length} open</StatusBadge>
          </div>
          {alertsResult.ok && todayActionsResult.ok ? (
            <TodayInbox items={inboxItems} selectedItem={selectedItem} />
          ) : (
            <div className="space-y-2 p-4">
              {!alertsResult.ok ? (
                <ErrorState title="Alerts unavailable" message={getApiErrorMessage(alertsResult.error)} />
              ) : null}
              {!todayActionsResult.ok ? (
                <ErrorState title="Actions unavailable" message={getApiErrorMessage(todayActionsResult.error)} />
              ) : null}
            </div>
          )}
        </section>

        <TodayDetail selectedItem={selectedItem} />
      </div>

      <RecentScansPanel
        scanJobs={scanJobs}
        error={scanJobsResult.ok ? undefined : getApiErrorMessage(scanJobsResult.error)}
      />
    </div>
  );
}

function AttentionLink({
  href,
  label,
  value,
}: {
  href: string;
  label: string;
  value: string | number;
}) {
  return (
    <Link href={href} className="flex items-center justify-between gap-3 px-4 py-3 transition hover:bg-slate-800">
      <span className="text-sm font-medium text-slate-400">{label}</span>
      <span className="font-mono text-sm font-semibold text-slate-100">{value}</span>
    </Link>
  );
}

function TodayInbox({
  items,
  selectedItem,
}: {
  items: InboxItem[];
  selectedItem?: InboxItem;
}) {
  if (items.length === 0) {
    return (
      <div className="px-4 py-8 text-sm text-slate-500">
        No open actions or unread alerts. New role reviews and due follow-ups will appear here.
      </div>
    );
  }

  return (
    <div className="divide-y divide-slate-800">
      {items.map((item) => {
        const isSelected = item.id === selectedItem?.id;
        const href =
          item.kind === "alert"
            ? `/?alert_id=${item.alert.id}`
            : `/?action_id=${item.action.id}`;
        const title = item.kind === "alert" ? item.alert.job_title : item.action.title;
        const company = item.kind === "alert" ? item.alert.company_name : item.action.company_name;
        const timestamp =
          item.kind === "alert"
            ? item.alert.created_at
            : item.action.due_at || item.action.created_at;

        return (
          <Link
            key={item.id}
            href={href}
            className={[
              "block border-l-2 px-4 py-3 transition hover:bg-slate-800",
              isSelected
                ? "border-indigo-300 bg-indigo-500/10"
                : "border-transparent",
            ].join(" ")}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <StatusBadge
                    tone={item.kind === "alert" ? "success" : actionTone(item.action.action_type)}
                    withDot
                  >
                    {item.kind === "alert" ? "New role" : actionLabel(item.action.action_type)}
                  </StatusBadge>
                  <span className="font-mono text-[11px] text-slate-600">
                    {formatDateTime(timestamp)}
                  </span>
                </div>
                <div className="mt-2 truncate font-medium text-slate-50">{title}</div>
                <div className="mt-1 truncate text-sm text-slate-500">
                  {company || "No company linked"}
                </div>
              </div>
              {item.kind === "alert" ? (
                <span className="font-mono text-xs text-emerald-300">ALERT</span>
              ) : (
                <span className="font-mono text-xs text-indigo-300">TASK</span>
              )}
            </div>
          </Link>
        );
      })}
    </div>
  );
}

function TodayDetail({ selectedItem }: { selectedItem?: InboxItem }) {
  if (!selectedItem) {
    return (
      <DetailDrawer title="Inbox clear" subtitle="No role alert or action is selected.">
        <p className="text-sm leading-6 text-slate-500">
          When scans discover new roles or follow-ups become due, the selected item details and actions will appear here.
        </p>
      </DetailDrawer>
    );
  }

  if (selectedItem.kind === "alert") {
    const alert = selectedItem.alert;

    return (
      <DetailDrawer
        eyebrow={`Inbox / Alert ${alert.id}`}
        title={alert.job_title}
        subtitle={`${alert.company_name} - ${formatDateTime(alert.created_at)}`}
        closeHref="/"
        footer={
          <div className="grid gap-2 sm:grid-cols-4 xl:grid-cols-2">
            <form action={saveAlertAsApplicationAction} className="sm:col-span-2 xl:col-span-1">
              <input type="hidden" name="alert_id" value={alert.id} />
              <Button type="submit" variant="primary" className="w-full">
                Save to Applications
              </Button>
            </form>
            <form action={skipAlertAsApplicationAction}>
              <input type="hidden" name="alert_id" value={alert.id} />
              <Button type="submit" variant="default" className="w-full">
                Skip
              </Button>
            </form>
            <form action={markAlertReadAction}>
              <input type="hidden" name="alert_id" value={alert.id} />
              <Button type="submit" variant="default" className="w-full">
                Mark read
              </Button>
            </form>
          </div>
        }
      >
        <div className="space-y-4">
          <div className="rounded-lg border border-slate-800 bg-slate-950 p-4">
            <div className="console-label">Alert message</div>
            <p className="mt-3 text-sm leading-6 text-slate-300">
              {alert.message || alert.title || "New matching role found during scan."}
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <SignalStat label="Company" value={alert.company_name} />
            <SignalStat label="Status" value={alert.status} />
            <SignalStat label="Alert type" value={alert.alert_type} />
            <SignalStat label="Job ID" value={alert.job_id} />
          </div>
          <ButtonLink
            href={alert.job_apply_url}
            target="_blank"
          >
            Open role
          </ButtonLink>
          <form action={dismissAlertAction}>
            <input type="hidden" name="alert_id" value={alert.id} />
            <button type="submit" className="h-8 text-xs font-semibold text-rose-300 transition hover:text-rose-200">
              Dismiss alert
            </button>
          </form>
        </div>
      </DetailDrawer>
    );
  }

  const action = selectedItem.action;

  return (
    <DetailDrawer
      eyebrow={`Inbox / Action ${action.id}`}
      title={action.title}
      subtitle={`${action.company_name || "Workspace"} - ${formatDateTime(action.due_at || action.created_at)}`}
      closeHref="/"
      footer={
        <div className="flex flex-wrap justify-end gap-2">
          <form action={completeTodayActionAction}>
            <input type="hidden" name="action_id" value={action.id} />
            <Button type="submit" variant="primary">
              Done
            </Button>
          </form>
          <form action={dismissTodayActionAction}>
            <input type="hidden" name="action_id" value={action.id} />
            <Button type="submit">
              Dismiss
            </Button>
          </form>
        </div>
      }
    >
      <div className="space-y-4">
        <div className="flex flex-wrap gap-2">
          <StatusBadge tone={actionTone(action.action_type)} withDot>
            {actionLabel(action.action_type)}
          </StatusBadge>
          <StatusBadge tone="neutral">{action.status}</StatusBadge>
        </div>
        <p className="rounded-lg border border-slate-800 bg-slate-950 p-4 text-sm leading-6 text-slate-300">
          {action.message || "No additional action context recorded."}
        </p>
        {action.source_alert_id ? (
          <div className="rounded-lg border border-slate-800 bg-slate-950 p-4">
            <div className="console-label">Application action</div>
            <form action={saveAlertAsApplicationAction} className="mt-3 grid gap-2">
              <input type="hidden" name="alert_id" value={action.source_alert_id} />
              <Input
                name="next_action"
                placeholder="Next action"
                className="mt-0"
              />
              <Input
                name="follow_up_at"
                type="date"
                className="mt-0"
              />
              <Button type="submit" variant="primary">
                Save to Applications
              </Button>
            </form>
          </div>
        ) : null}
        {action.apply_url ? (
          <Link href={action.apply_url} target="_blank" className="inline-flex text-sm font-semibold text-cyan-300 hover:text-cyan-200">
            Open linked role
          </Link>
        ) : null}
      </div>
    </DetailDrawer>
  );
}

function SignalStat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-md border border-slate-800 bg-slate-950 px-3 py-2">
      <div className="console-label">{label}</div>
      <div className="mt-2 truncate text-sm font-semibold text-slate-100">{value}</div>
    </div>
  );
}

function RecentScansPanel({
  scanJobs,
  error,
}: {
  scanJobs: ScanJob[];
  error?: string;
}) {
  return (
    <section className="rounded-lg border border-slate-800 bg-slate-900">
      <div className="border-b border-slate-800 px-4 py-3">
        <h2 className="text-sm font-semibold text-slate-50">Recent scan jobs</h2>
      </div>
      {error ? (
        <div className="px-4 py-3 text-sm text-rose-300">{error}</div>
      ) : scanJobs.length === 0 ? (
        <div className="px-4 py-5 text-sm text-slate-500">
          No scan jobs yet. Run due scans or scan a company manually.
        </div>
      ) : (
        <div className="divide-y divide-slate-800">
          {scanJobs.map((scanJob) => (
            <div key={scanJob.id} className="grid gap-2 px-4 py-3 sm:grid-cols-[minmax(0,1fr)_auto]">
              <div className="min-w-0">
                <div className="font-medium text-slate-50">{scanJob.company_name}</div>
                <div className="mt-1 font-mono text-[11px] text-slate-600">
                  {scanJob.trigger} - {formatDateTime(scanJob.finished_at || scanJob.started_at)}
                </div>
                <div className="mt-1 text-xs leading-5 text-slate-500">
                  Found {scanJob.jobs_found}, created {scanJob.jobs_created}, alerts {scanJob.alerts_created}
                </div>
              </div>
              <div className="flex items-start sm:justify-end">
                <StatusBadge tone={scanStatusTone(scanJob.status)} withDot>
                  {scanJob.status}
                </StatusBadge>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function actionTone(actionType: string) {
  switch (actionType) {
    case "review_new_role":
      return "info" as const;
    case "follow_up":
      return "warning" as const;
    default:
      return "neutral" as const;
  }
}

function actionLabel(actionType: string) {
  switch (actionType) {
    case "review_new_role":
      return "Review role";
    case "follow_up":
      return "Follow-up";
    default:
      return actionType.replaceAll("_", " ");
  }
}

function scanStatusTone(status: string) {
  switch (status) {
    case "success":
      return "success" as const;
    case "failed":
      return "danger" as const;
    case "running":
    case "queued":
      return "warning" as const;
    default:
      return "neutral" as const;
  }
}

function formatDateTime(value: string | null) {
  if (!value) {
    return "Not recorded";
  }

  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function getSearchParam(
  params: Record<string, string | string[] | undefined>,
  key: string,
) {
  const value = params[key];
  return Array.isArray(value) ? value[0] : value;
}
