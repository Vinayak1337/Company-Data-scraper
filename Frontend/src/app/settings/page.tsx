import type { InputHTMLAttributes, ReactNode } from "react";
import { Cpu, Terminal, Workflow } from "lucide-react";
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
import { updateNotificationPreferencesAction } from "./actions";

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
  const apiProviders = providers.filter((provider) => !provider.is_local_only);
  const cliProviders = providers.filter((provider) => provider.is_local_only);

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_380px]">
      <PageSection
        title="Providers"
        description="Provider setup is terminal-only. Use ./jobscout providers to select the project brain and write Backend/.env."
      >
        <div className="space-y-4 p-4">
          <div className="rounded-md border border-[var(--line)] bg-[var(--bg-sunken)] p-3 font-mono text-xs text-[var(--ink-2)]">
            ./jobscout providers
          </div>
          <ProviderGroup
            icon={<Cpu className="h-4 w-4" aria-hidden />}
            title="API providers"
            description="Use these from the web app once the local env vars are present."
            providers={apiProviders}
          />
          <ProviderGroup
            icon={<Terminal className="h-4 w-4" aria-hidden />}
            title="Local CLI providers"
            description="These stay worker/local only. Enable after the CLI is installed, logged in, and JOB_SCOUT_ENABLE_LOCAL_CLI=true is set."
            providers={cliProviders}
          />
        </div>
      </PageSection>
      <RuntimeSettings runtime={runtime} />
    </div>
  );
}

function ProviderGroup({
  icon,
  title,
  description,
  providers,
}: {
  icon: ReactNode;
  title: string;
  description: string;
  providers: AgentProvider[];
}) {
  if (!providers.length) {
    return null;
  }

  return (
    <div className="space-y-3">
      <div className="flex items-start gap-2">
        <div className="mt-0.5 text-[var(--accent)]">{icon}</div>
        <div className="min-w-0">
          <h3 className="text-sm font-medium text-[var(--ink)]">{title}</h3>
          <p className="mt-0.5 text-xs leading-5 text-[var(--ink-3)]">{description}</p>
        </div>
      </div>
      <div className="space-y-3">
        {providers.map((provider) => (
          <ProviderCard key={provider.provider} provider={provider} />
        ))}
      </div>
    </div>
  );
}

function ProviderCard({ provider }: { provider: AgentProvider }) {
  return (
    <div
      className="rounded-md border border-[var(--line)] bg-[var(--bg-sunken)] p-4"
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h4 className="text-sm font-semibold text-[var(--ink)]">{provider.label}</h4>
            <ProviderStatusBadges provider={provider} />
          </div>
          <div className="mt-1 font-mono text-[11px] text-[var(--faint)]">{provider.provider}</div>
          {provider.setup_hint ? (
            <p className="mt-2 max-w-3xl text-xs leading-5 text-[var(--ink-3)]">{provider.setup_hint}</p>
          ) : null}
        </div>
        <StatusBadge tone={provider.is_brain ? "success" : "neutral"} withDot>
          {provider.is_brain ? "Brain" : "Standby"}
        </StatusBadge>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        <ProviderReadout label={provider.is_local_only ? "CLI profile" : "Model"} value={provider.model_name || "default"} />
        {provider.is_local_only ? (
          <ProviderReadout icon={<Terminal className="h-3.5 w-3.5" aria-hidden />} label="Command" value={provider.local_cli_command || "not configured"} />
        ) : (
          <ProviderReadout label="Key env var" value={provider.api_key_env_var || "not required"} />
        )}
        <ProviderReadout label="Daily limit" value={String(provider.daily_run_limit)} />
      </div>

      <div className="mt-4 flex flex-wrap gap-2 border-t border-[var(--line)] pt-3">
        <StatusBadge tone={provider.enabled ? "success" : "neutral"}>{provider.enabled ? "Enabled" : "Disabled"}</StatusBadge>
        <StatusBadge tone={provider.consent_required ? "warning" : "neutral"}>
          {provider.consent_required ? "Consent required" : "No consent gate"}
        </StatusBadge>
      </div>
    </div>
  );
}

function ProviderStatusBadges({ provider }: { provider: AgentProvider }) {
  return (
    <>
      <StatusBadge tone={provider.enabled ? "success" : "neutral"} withDot>
        {provider.enabled ? "Enabled" : "Disabled"}
      </StatusBadge>
      <StatusBadge tone={provider.is_local_only ? "warning" : "info"}>
        {provider.is_local_only ? "Local CLI" : "API"}
      </StatusBadge>
      {provider.is_local_only ? (
        <StatusBadge tone={provider.local_cli_command_found ? "success" : "warning"}>
          {provider.local_cli_command_found ? "Command found" : "Command missing"}
        </StatusBadge>
      ) : provider.configuration_status === "ready" ? (
        <StatusBadge tone="success">Ready</StatusBadge>
      ) : provider.api_key_env_var ? (
        <StatusBadge tone={provider.api_key_configured ? "success" : "warning"}>
          {provider.api_key_configured ? "Key found" : "Key missing"}
        </StatusBadge>
      ) : null}
    </>
  );
}

function ProviderReadout({
  icon,
  label,
  value,
}: {
  icon?: ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div>
      <span className="text-xs font-medium text-[var(--muted)]">{label}</span>
      <div className="mt-1 flex h-8 items-center gap-2 rounded-[3px] border border-[var(--line)] bg-[var(--bg-raised)] px-3 font-mono text-[12px] text-[var(--ink-2)]">
        {icon ? <span className="text-[var(--accent)]">{icon}</span> : null}
        <span className="truncate">{value}</span>
      </div>
    </div>
  );
}

function RuntimeSettings({ runtime }: { runtime: AgentRuntimeStatus | null }) {
  const providers = runtime?.providers ?? [];
  return (
    <PageSection
      title="Runtime"
      description="Current process state. CLI readiness is intentionally tied to this local shell."
    >
      <div className="space-y-4 p-4">
        <div className="grid gap-3 sm:grid-cols-2">
          <RuntimeStat icon={<Workflow className="h-4 w-4" aria-hidden />} label="Execution" value={runtime?.execution_mode ?? "unknown"} />
          <RuntimeStat icon={<Terminal className="h-4 w-4" aria-hidden />} label="Environment" value={runtime?.runtime_environment ?? "unknown"} />
          <RuntimeStat label="Brain" value={runtime?.brain_provider ?? "direct_api"} />
          <RuntimeStat label="Queued" value={String(runtime?.queued_runs ?? 0)} />
          <RuntimeStat label="Running" value={String(runtime?.running_runs ?? 0)} />
        </div>
        <div className="rounded-md border border-[var(--line)] bg-[var(--bg-sunken)] p-3">
          <div className="flex items-center justify-between gap-3">
            <div>
              <div className="text-xs font-medium text-[var(--ink)]">Local CLI gate</div>
              <div className="mt-1 text-xs text-[var(--ink-3)]">Set from JOB_SCOUT_ENABLE_LOCAL_CLI.</div>
            </div>
            <StatusBadge tone={runtime?.local_cli_enabled ? "success" : "neutral"} withDot>
              {runtime?.local_cli_enabled ? "Open" : "Closed"}
            </StatusBadge>
          </div>
        </div>
        <div className="space-y-2">
          {providers.map((provider) => {
            const item = provider as Partial<AgentProvider>;
            return (
              <div key={String(item.provider)} className="flex items-center justify-between gap-3 border-t border-[var(--line)] pt-2 text-xs">
                <span className="truncate text-[var(--ink-2)]">{item.label || item.provider}</span>
                <span className="font-mono text-[var(--faint)]">{item.configuration_status || "unknown"}</span>
              </div>
            );
          })}
        </div>
      </div>
    </PageSection>
  );
}

function RuntimeStat({
  icon,
  label,
  value,
}: {
  icon?: ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-md border border-[var(--line)] bg-[var(--bg-sunken)] p-3">
      <div className="flex items-center gap-2 text-xs text-[var(--ink-3)]">
        {icon ? <span className="text-[var(--accent)]">{icon}</span> : null}
        {label}
      </div>
      <div className="mt-2 truncate font-mono text-sm text-[var(--ink)]">{value}</div>
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
