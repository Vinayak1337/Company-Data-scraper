import type { InputHTMLAttributes } from "react";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";
import { Input, Select } from "@/components/ui/form-controls";
import { PageHeader } from "@/components/ui/page-header";
import { PageSection } from "@/components/ui/page-section";
import { StatusBadge } from "@/components/ui/status-badge";
import { SystemBanner } from "@/components/ui/system-banner";
import { Tabs } from "@/components/ui/tabs";
import {
  type AgentRuntimeStatus,
  getAgentRuntime,
  getApiErrorMessage,
  getBackendApiBaseUrl,
  getBackendHealth,
  getDiagnostics,
  getNotificationPreferences,
  listAgentProviders,
  toApiResult,
} from "@/lib/api";
import type { AgentProvider, NotificationPreferences } from "@/lib/api";
import { updateAgentProviderAction, updateNotificationPreferencesAction } from "./actions";

type SettingsPageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function SettingsPage({ searchParams }: SettingsPageProps) {
  const params = await searchParams;
  const settingsError = getSearchParam(params, "settings_error");
  const settingsNotice = getSearchParam(params, "settings_notice");
  const activeTab = getSearchParam(params, "tab") || "ai";

  const [healthResult, diagnosticsResult, preferencesResult, providersResult, runtimeResult] = await Promise.all([
    toApiResult(getBackendHealth()),
    toApiResult(getDiagnostics()),
    toApiResult(getNotificationPreferences()),
    toApiResult(listAgentProviders()),
    toApiResult(getAgentRuntime()),
  ]);

  const backendOnline = healthResult.ok && String(healthResult.data.status).toLowerCase() === "ok";

  return (
    <div className="space-y-4">
      <PageHeader
        title="Settings"
        eyebrow="AI and notifications"
        description="Configure the two things V3 needs before useful emails can happen: agent runtime and notification thresholds."
        actions={
          <StatusBadge tone={backendOnline ? "success" : "danger"} withDot>
            {backendOnline ? "Backend online" : "Backend down"}
          </StatusBadge>
        }
      />

      {settingsNotice ? <SystemBanner tone="success">{settingsNotice}</SystemBanner> : null}
      {settingsError ? <SystemBanner tone="danger">{settingsError}</SystemBanner> : null}

      <Tabs
        items={[
          { href: "/settings?tab=ai", label: "AI", active: activeTab === "ai" },
          { href: "/settings?tab=notifications", label: "Notifications", active: activeTab === "notifications" },
          { href: "/settings?tab=health", label: "Health", active: activeTab === "health" },
        ]}
      />

      {activeTab === "ai" ? (
        providersResult.ok ? (
          <AiSettings providers={providersResult.data.results} runtime={runtimeResult.ok ? runtimeResult.data : null} />
        ) : (
          <ErrorState title="AI settings unavailable" message={getApiErrorMessage(providersResult.error)} />
        )
      ) : null}

      {activeTab === "notifications" ? (
        preferencesResult.ok ? (
          <NotificationSettings preferences={preferencesResult.data} />
        ) : (
          <ErrorState title="Notification settings unavailable" message={getApiErrorMessage(preferencesResult.error)} />
        )
      ) : null}

      {activeTab === "health" ? (
        <PageSection title="Backend health" description={getBackendApiBaseUrl()}>
          <pre className="overflow-auto p-4 text-xs leading-5 text-[var(--muted)]">
            {JSON.stringify(
              {
                health: healthResult.ok ? healthResult.data : getApiErrorMessage(healthResult.error),
                diagnostics: diagnosticsResult.ok ? diagnosticsResult.data : getApiErrorMessage(diagnosticsResult.error),
              },
              null,
              2,
            )}
          </pre>
        </PageSection>
      ) : null}
    </div>
  );
}

function AiSettings({
  providers,
  runtime,
}: {
  providers: AgentProvider[];
  runtime: AgentRuntimeStatus | null;
}) {
  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
      <PageSection title="Providers" description="Direct API is enabled by default for local deterministic agent reviews. Add env vars before enabling hosted providers.">
        <div className="divide-y divide-[var(--border)]">
          {providers.map((provider) => (
            <form key={provider.provider} action={updateAgentProviderAction} className="grid gap-3 p-4 lg:grid-cols-[180px_minmax(0,1fr)_160px_120px_auto] lg:items-end">
              <input type="hidden" name="provider" value={provider.provider} />
              <div>
                <div className="text-sm font-semibold text-[var(--ink)]">{provider.label}</div>
                <div className="mt-1 font-mono text-[11px] text-[var(--faint)]">{provider.provider}</div>
              </div>
              <TextInput label="Model" name="model_name" defaultValue={provider.model_name} />
              <TextInput label="Key env var" name="api_key_env_var" defaultValue={provider.api_key_env_var} />
              <TextInput label="Daily limit" name="daily_run_limit" type="number" defaultValue={String(provider.daily_run_limit)} />
              <div className="flex items-center gap-3">
                <label className="flex items-center gap-2 text-sm text-[var(--muted)]">
                  <input name="enabled" type="checkbox" defaultChecked={provider.enabled} />
                  Enabled
                </label>
                <label className="flex items-center gap-2 text-sm text-[var(--muted)]">
                  <input name="consent_required" type="checkbox" defaultChecked={provider.consent_required} />
                  Consent
                </label>
                <Button type="submit" variant="primary">Save</Button>
              </div>
            </form>
          ))}
        </div>
      </PageSection>
      <PageSection title="Runtime">
        <pre className="overflow-auto p-4 text-xs leading-5 text-[var(--muted)]">{JSON.stringify(runtime, null, 2)}</pre>
      </PageSection>
    </div>
  );
}

function NotificationSettings({ preferences }: { preferences: NotificationPreferences }) {
  return (
    <PageSection title="Notification preferences" description="These thresholds are the guardrails. The AI can recommend, but it cannot notify below your saved settings.">
      <form action={updateNotificationPreferencesAction} className="grid gap-4 p-4 md:grid-cols-2">
        <TextInput label="Email address" name="email_address" type="email" defaultValue={preferences.email_address} />
        <label>
          <span className="text-xs font-medium text-[var(--muted)]">Digest frequency</span>
          <Select name="digest_frequency" defaultValue={preferences.digest_frequency}>
            <option value="immediate">Immediate</option>
            <option value="daily">Daily</option>
            <option value="weekdays">Weekdays</option>
            <option value="weekly">Weekly</option>
            <option value="disabled">Disabled</option>
          </Select>
        </label>
        <TextInput label="Digest time" name="digest_time" type="time" defaultValue={preferences.digest_time} />
        <TextInput label="Timezone" name="timezone" defaultValue={preferences.timezone} />
        <TextInput label="Minimum match score" name="minimum_match_score" type="number" min="0" max="100" defaultValue={String(preferences.minimum_match_score)} />
        <TextInput label="Minimum confidence" name="minimum_confidence_score" type="number" min="0" max="100" defaultValue={String(preferences.minimum_confidence_score)} />
        <TextInput label="Max digest items" name="max_digest_items" type="number" min="1" max="100" defaultValue={String(preferences.max_digest_items)} />
        <label>
          <span className="text-xs font-medium text-[var(--muted)]">Channel</span>
          <Select name="digest_channel" defaultValue={preferences.digest_channel}>
            <option value="email">Email</option>
            <option value="local">Local only</option>
          </Select>
        </label>
        <div className="flex flex-wrap gap-4 md:col-span-2">
          <label className="flex items-center gap-2 text-sm text-[var(--muted)]">
            <input name="digest_enabled" type="checkbox" defaultChecked={preferences.digest_enabled} />
            Digest enabled
          </label>
          <label className="flex items-center gap-2 text-sm text-[var(--muted)]">
            <input name="immediate_email_enabled" type="checkbox" defaultChecked={preferences.immediate_email_enabled} />
            Immediate email
          </label>
          <label className="flex items-center gap-2 text-sm text-[var(--muted)]">
            <input name="quiet_hours_enabled" type="checkbox" defaultChecked={preferences.quiet_hours_enabled} />
            Quiet hours
          </label>
        </div>
        <TextInput label="Quiet starts" name="quiet_hours_start" type="time" defaultValue={preferences.quiet_hours_start} />
        <TextInput label="Quiet ends" name="quiet_hours_end" type="time" defaultValue={preferences.quiet_hours_end} />
        <div className="flex justify-end md:col-span-2">
          <Button type="submit" variant="primary">Save preferences</Button>
        </div>
      </form>
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

function getSearchParam(
  params: Record<string, string | string[] | undefined>,
  key: string,
) {
  const value = params[key];
  return Array.isArray(value) ? value[0] : value;
}
