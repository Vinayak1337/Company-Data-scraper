import {
  DiagnosticsPanel,
  DeletePersonalDataPanel,
  ExportPanel,
  ImportCompanyWatchlistPanel,
  ImportWorkspacePanel,
  NotificationPreferencesPanel,
} from "@/components/settings/settings-panels";
import { PageHeader } from "@/components/ui/page-header";
import { StatusBadge } from "@/components/ui/status-badge";
import { SystemBanner } from "@/components/ui/system-banner";
import { Tabs } from "@/components/ui/tabs";
import {
  ApiError,
  exportWorkspaceData,
  getApiErrorMessage,
  getBackendApiBaseUrl,
  getBackendHealth,
  getDiagnostics,
  getNotificationPreferences,
  listCompanies,
  toApiResult,
} from "@/lib/api";
import type { ApiResult, WorkspaceExport } from "@/lib/api";
import {
  deleteAllPersonalDataAction,
  importCompanyWatchlistAction,
  importWorkspaceAction,
  updateNotificationPreferencesAction,
} from "./actions";

type SettingsPageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function SettingsPage({
  searchParams,
}: SettingsPageProps) {
  const params = await searchParams;
  const exportRequested = getSearchParam(params, "export") === "1";
  const settingsError = getSearchParam(params, "settings_error");
  const settingsNotice = getSearchParam(params, "settings_notice");
  const activeTab = getSearchParam(params, "tab") || "health";
  const exportPromise: Promise<ApiResult<WorkspaceExport> | null> =
    exportRequested ? toApiResult(getExportPayload()) : Promise.resolve(null);

  const [healthResult, diagnosticsResult, notificationPreferencesResult, exportResult] = await Promise.all([
    toApiResult(getBackendHealth()),
    toApiResult(getDiagnostics()),
    toApiResult(getNotificationPreferences()),
    exportPromise,
  ]);

  const backendOnline =
    healthResult.ok && String(healthResult.data.status).toLowerCase() === "ok";
  const exportJson = exportResult?.ok
    ? JSON.stringify(exportResult.data, null, 2)
    : undefined;
  const exportError =
    exportResult && !exportResult.ok
      ? getApiErrorMessage(exportResult.error)
      : undefined;

  return (
    <div className="space-y-4">
      <PageHeader
        title="Settings"
        eyebrow="Workspace"
        description="Inspect backend readiness and move company watchlist data in or out without browser-side API calls."
        actions={
          <StatusBadge tone={backendOnline ? "success" : "danger"} withDot>
            {backendOnline ? "Backend online" : "Backend down"}
          </StatusBadge>
        }
      />

      {settingsNotice ? <SystemBanner tone="success">{settingsNotice}</SystemBanner> : null}

      {settingsError ? (
        <SystemBanner tone="danger">{settingsError}</SystemBanner>
      ) : null}

      <Tabs
        items={[
          { href: "/settings?tab=health", label: "Health", active: activeTab === "health" },
          { href: "/settings?tab=notifications", label: "Notifications", active: activeTab === "notifications" },
          { href: "/settings?tab=ownership", label: "Data Ownership", active: activeTab === "ownership" },
          { href: "/settings?tab=danger", label: "Danger Zone", active: activeTab === "danger" },
        ]}
      />

      {activeTab === "health" ? (
        <DiagnosticsPanel
          backendUrl={getBackendApiBaseUrl()}
          backendHealth={healthResult.ok ? healthResult.data : undefined}
          diagnostics={diagnosticsResult.ok ? diagnosticsResult.data : undefined}
          diagnosticsError={
            diagnosticsResult.ok
              ? undefined
              : getApiErrorMessage(diagnosticsResult.error)
          }
        />
      ) : null}

      {activeTab === "notifications" ? (
        <NotificationPreferencesPanel
          preferences={notificationPreferencesResult.ok ? notificationPreferencesResult.data : undefined}
          preferencesError={
            notificationPreferencesResult.ok
              ? undefined
              : getApiErrorMessage(notificationPreferencesResult.error)
          }
          action={updateNotificationPreferencesAction}
        />
      ) : null}

      {activeTab === "ownership" ? (
        <div className="grid gap-4 xl:grid-cols-2">
        <ExportPanel
          exportRequested={exportRequested}
          exportJson={exportJson}
          exportError={exportError}
        />
        <ImportCompanyWatchlistPanel action={importCompanyWatchlistAction} />
        <ImportWorkspacePanel action={importWorkspaceAction} />
        </div>
      ) : null}

      {activeTab === "danger" ? (
        <DeletePersonalDataPanel action={deleteAllPersonalDataAction} />
      ) : null}
    </div>
  );
}

async function getExportPayload(): Promise<WorkspaceExport> {
  try {
    return await exportWorkspaceData();
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      const companies = await listCompanies();

      return {
        app_version: "frontend-fallback",
        generated_at: new Date().toISOString(),
        companies: companies.results,
        jobs: [],
        meta: {
          source: "companies-list-fallback",
          reason: "Backend export endpoint is not available.",
        },
      };
    }

    throw error;
  }
}

function getSearchParam(
  params: Record<string, string | string[] | undefined>,
  key: string,
) {
  const value = params[key];
  return Array.isArray(value) ? value[0] : value;
}
