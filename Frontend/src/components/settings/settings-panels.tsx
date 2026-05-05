import { Button } from "@/components/ui/button";
import { DangerAction } from "@/components/ui/danger-action";
import { Input, Select, Textarea } from "@/components/ui/form-controls";
import { PageSection } from "@/components/ui/page-section";
import { StatusBadge } from "@/components/ui/status-badge";
import { SystemBanner } from "@/components/ui/system-banner";
import type {
  BackendHealth,
  DiagnosticCheck,
  DiagnosticsResponse,
  NotificationPreferences,
} from "@/lib/api";

type DiagnosticsPanelProps = {
  backendUrl: string;
  backendHealth?: BackendHealth;
  diagnostics?: DiagnosticsResponse;
  diagnosticsError?: string;
};

type ExportPanelProps = {
  exportRequested: boolean;
  exportJson?: string;
  exportError?: string;
};

type ImportCompanyWatchlistPanelProps = {
  action: (formData: FormData) => Promise<void>;
};

type ImportWorkspacePanelProps = {
  action: (formData: FormData) => Promise<void>;
};

type DeletePersonalDataPanelProps = {
  action: (formData: FormData) => Promise<void>;
};

type NotificationPreferencesPanelProps = {
  preferences?: NotificationPreferences;
  preferencesError?: string;
  action: (formData: FormData) => Promise<void>;
};

const sampleImportJson = JSON.stringify(
  {
    companies: [
      {
        name: "Example",
        careers_url: "https://jobs.lever.co/example",
        priority_tier: "normal",
        title_keywords: ["engineer", "developer"],
        negative_title_keywords: ["intern"],
        location_keywords: ["India", "Remote"],
        work_mode_filter: "remote",
      },
    ],
  },
  null,
  2,
);

export function DiagnosticsPanel({
  backendUrl,
  backendHealth,
  diagnostics,
  diagnosticsError,
}: DiagnosticsPanelProps) {
  const checks = normalizeDiagnostics(diagnostics, backendHealth);

  return (
    <PageSection
      title="Diagnostics"
      description="Backend readiness checks and local API reachability."
      actions={<span className="block max-w-72 truncate text-xs text-[var(--faint)]">{backendUrl}</span>}
    >
      {diagnosticsError ? (
        <div className="border-b border-[var(--border)] p-3">
          <SystemBanner tone="warning">{diagnosticsError}</SystemBanner>
        </div>
      ) : null}

      <div className="grid gap-3 p-3 md:grid-cols-2 xl:grid-cols-3">
        {checks.map((check) => (
          <div
            key={check.name}
            className="rounded-md border border-[var(--border)] bg-[var(--surface-recessed)] px-3 py-3"
          >
            <div className="flex items-center justify-between gap-2">
              <div className="truncate text-xs font-semibold text-[var(--muted)]">
                {check.name}
              </div>
              <StatusBadge tone={statusTone(check.status)} withDot>
                {check.status || "unknown"}
              </StatusBadge>
            </div>
            {check.message ? (
              <p className="mt-2 text-xs leading-5 text-[var(--muted)]">
                {check.message}
              </p>
            ) : null}
            {check.detail !== undefined ? (
              <pre className="mt-2 max-h-24 overflow-auto rounded-md border border-[var(--border)] bg-[var(--surface)] px-2 py-1.5 text-[11px] leading-5 text-[var(--muted)]">
                {stringifyDetail(check.detail)}
              </pre>
            ) : null}
          </div>
        ))}
      </div>
    </PageSection>
  );
}

export function ExportPanel({
  exportRequested,
  exportJson,
  exportError,
}: ExportPanelProps) {
  const downloadHref = exportJson
    ? `data:application/json;charset=utf-8,${encodeURIComponent(exportJson)}`
    : undefined;

  return (
    <PageSection
      title="Export"
      description="Generate a JSON snapshot without exposing secrets."
      actions={
        <form action="/settings" method="get">
          <input type="hidden" name="tab" value="ownership" />
          <Button
            type="submit"
            name="export"
            value="1"
            size="sm"
            variant="primary"
          >
            Generate JSON
          </Button>
        </form>
      }
    >

      {exportError ? (
        <div className="border-b border-[var(--border)] p-3">
          <SystemBanner tone="danger">{exportError}</SystemBanner>
        </div>
      ) : null}

      {exportJson ? (
        <div className="space-y-3 p-4">
          <Textarea
            readOnly
            defaultValue={exportJson}
            className="min-h-72 font-mono text-xs"
          />
          <div className="flex justify-end">
            <a
              href={downloadHref}
              download="company-tracker-export.json"
              className="inline-flex h-8 items-center rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 text-xs font-semibold text-[var(--text)] transition hover:border-[var(--border-strong)] hover:bg-[var(--surface-hover)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
            >
              Download JSON
            </a>
          </div>
        </div>
      ) : !exportRequested ? (
        <div className="px-4 py-5 text-sm text-[var(--muted)]">
          No export generated in this view.
        </div>
      ) : null}
    </PageSection>
  );
}

export function ImportCompanyWatchlistPanel({
  action,
}: ImportCompanyWatchlistPanelProps) {
  return (
    <PageSection
      title="Import company watchlist"
      description="Paste JSON with a companies, watchlist, or company_watchlist array."
    >
      <form action={action} className="space-y-3 p-4">
        <label className="block">
          <span className="text-xs font-medium text-[var(--muted)]">
            Watchlist JSON
          </span>
          <Textarea
            name="import_json"
            defaultValue={sampleImportJson}
            className="min-h-72 font-mono text-xs"
          />
        </label>
        <div className="flex justify-end">
          <Button type="submit" size="sm" variant="primary">
            Import watchlist
          </Button>
        </div>
      </form>
    </PageSection>
  );
}

export function ImportWorkspacePanel({ action }: ImportWorkspacePanelProps) {
  return (
    <PageSection
      title="Restore workspace"
      description="Import a complete export JSON. Existing records are updated where stable IDs or URLs match."
    >
      <form action={action} className="space-y-3 p-4">
        <label className="block">
          <span className="text-xs font-medium text-[var(--muted)]">Workspace export JSON</span>
          <Textarea
            name="workspace_json"
            placeholder='{"app_version":"0.1.0","companies":[],"jobs":[]}'
            className="min-h-56 font-mono text-xs"
          />
        </label>
        <div className="flex justify-end">
          <Button type="submit" size="sm" variant="primary">
            Restore workspace
          </Button>
        </div>
      </form>
    </PageSection>
  );
}

export function DeletePersonalDataPanel({ action }: DeletePersonalDataPanelProps) {
  return (
    <DangerAction
      title="Delete personal data"
      description="Removes profile, companies, jobs, applications, agents, analytics, and local settings from this workspace."
    >
      <form action={action} className="space-y-3 p-4">
        <label className="block">
          <span className="text-xs font-medium text-[var(--muted)]">Confirmation phrase</span>
          <Input
            name="delete_confirmation"
            placeholder="DELETE ALL PERSONAL DATA"
          />
        </label>
        <div className="flex justify-end">
          <Button type="submit" size="sm" variant="danger">
            Delete data
          </Button>
        </div>
      </form>
    </DangerAction>
  );
}

export function NotificationPreferencesPanel({
  preferences,
  preferencesError,
  action,
}: NotificationPreferencesPanelProps) {
  return (
    <PageSection
      title="Notification preferences"
      description="Control quiet hours and local digest cadence for future delivery channels."
      actions={
        preferences ? (
          <StatusBadge tone={preferences.quiet_hours_active ? "warning" : "neutral"} withDot>
            {preferences.quiet_hours_active ? "Quiet hours" : "Deliverable"}
          </StatusBadge>
        ) : null
      }
    >

      {preferencesError ? (
        <div className="border-b border-[var(--border)] p-3">
          <SystemBanner tone="danger">{preferencesError}</SystemBanner>
        </div>
      ) : null}

      {preferences ? (
        <form action={action} className="grid gap-4 p-4 lg:grid-cols-2">
          <div className="space-y-3 rounded-md border border-[var(--border)] bg-[var(--surface-recessed)] p-3">
            <label className="flex items-center justify-between gap-3 text-sm font-semibold text-[var(--text)]">
              Quiet hours
              <input
                type="checkbox"
                name="quiet_hours_enabled"
                defaultChecked={preferences.quiet_hours_enabled}
                className="h-4 w-4 rounded border-[var(--border)] text-[var(--primary)]"
              />
            </label>
            <div className="grid gap-2 sm:grid-cols-2">
              <TimeInput label="Start" name="quiet_hours_start" defaultValue={preferences.quiet_hours_start} />
              <TimeInput label="End" name="quiet_hours_end" defaultValue={preferences.quiet_hours_end} />
            </div>
            <label className="block">
              <span className="text-xs font-medium text-[var(--muted)]">Timezone</span>
              <Input
                name="timezone"
                defaultValue={preferences.timezone}
              />
            </label>
          </div>

          <div className="space-y-3 rounded-md border border-[var(--border)] bg-[var(--surface-recessed)] p-3">
            <label className="flex items-center justify-between gap-3 text-sm font-semibold text-[var(--text)]">
              Digest
              <input
                type="checkbox"
                name="digest_enabled"
                defaultChecked={preferences.digest_enabled}
                className="h-4 w-4 rounded border-[var(--border)] text-[var(--primary)]"
              />
            </label>
            <div className="grid gap-2 sm:grid-cols-2">
              <label className="block">
                <span className="text-xs font-medium text-[var(--muted)]">Cadence</span>
                <Select
                  name="digest_frequency"
                  defaultValue={preferences.digest_frequency}
                >
                  <option value="daily">Daily</option>
                  <option value="weekdays">Weekdays</option>
                  <option value="weekly">Weekly</option>
                </Select>
              </label>
              <TimeInput label="Delivery time" name="digest_time" defaultValue={preferences.digest_time} />
            </div>
            <label className="block">
              <span className="text-xs font-medium text-[var(--muted)]">Channel</span>
              <Select
                name="digest_channel"
                defaultValue={preferences.digest_channel}
              >
                <option value="local">Local</option>
                <option value="email">Email</option>
              </Select>
            </label>
          </div>

          <div className="flex justify-end lg:col-span-2">
            <Button type="submit" variant="primary">
              Save preferences
            </Button>
          </div>
        </form>
      ) : (
        <div className="px-4 py-5 text-sm text-[var(--muted)]">
          Notification preferences could not be loaded.
        </div>
      )}
    </PageSection>
  );
}

function TimeInput({
  label,
  name,
  defaultValue,
}: {
  label: string;
  name: string;
  defaultValue: string;
}) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-[var(--muted)]">{label}</span>
      <Input
        type="time"
        name={name}
        defaultValue={defaultValue}
      />
    </label>
  );
}

function normalizeDiagnostics(
  diagnostics: DiagnosticsResponse | undefined,
  backendHealth: BackendHealth | undefined,
): DiagnosticCheck[] {
  const checks: DiagnosticCheck[] = [];

  if (backendHealth) {
    checks.push({
      name: "Backend health",
      status: backendHealth.status,
      message: backendHealth.status === "ok" ? "API reachable" : "API returned an error",
    });
  }

  if (!diagnostics) {
    return checks.length
      ? checks
      : [{ name: "Backend health", status: "unknown", message: "Not checked" }];
  }

  if (Array.isArray(diagnostics.checks)) {
    checks.push(...diagnostics.checks);
  }

  for (const key of Object.keys(diagnostics)) {
    if (["status", "generated_at", "checks", "counts"].includes(key)) {
      continue;
    }

    const value = diagnostics[key];
    if (value === undefined || value === null) {
      continue;
    }

    checks.push(normalizeCheck(key, value));
  }

  if (diagnostics.counts) {
    checks.push({
      name: "Counts",
      status: "ok",
      detail: diagnostics.counts,
    });
  }

  return checks;
}

function normalizeCheck(key: string, value: unknown): DiagnosticCheck {
  if (typeof value === "string") {
    return {
      name: humanizeKey(key),
      status: "unknown",
      message: value,
    };
  }

  if (isRecord(value)) {
    return {
      name: getString(value.name) || humanizeKey(key),
      status: getString(value.status) || "unknown",
      message: getString(value.message),
      detail: value.detail ?? withoutDisplayFields(value),
      checked_at: getString(value.checked_at) || null,
    };
  }

  return {
    name: humanizeKey(key),
    status: "unknown",
    detail: value,
  };
}

function withoutDisplayFields(record: Record<string, unknown>) {
  const entries = Object.entries(record).filter(
    ([key]) => !["name", "status", "message", "checked_at"].includes(key),
  );

  return entries.length ? Object.fromEntries(entries) : undefined;
}

function stringifyDetail(value: unknown) {
  if (typeof value === "string") {
    return value;
  }

  return JSON.stringify(value, null, 2);
}

function getString(value: unknown) {
  return typeof value === "string" ? value : "";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function humanizeKey(key: string) {
  return key
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function statusTone(status: string) {
  switch (status) {
    case "ok":
    case "success":
      return "success" as const;
    case "warning":
    case "warn":
      return "warning" as const;
    case "error":
    case "failed":
    case "down":
      return "danger" as const;
    default:
      return "neutral" as const;
  }
}
