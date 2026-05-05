import Link from "next/link";
import { Button } from "@/components/ui/button";
import { DetailDrawer } from "@/components/ui/detail-drawer";
import { ErrorState } from "@/components/ui/error-state";
import { Input, Select, Textarea } from "@/components/ui/form-controls";
import { MetricCard } from "@/components/ui/metric-card";
import { PageHeader } from "@/components/ui/page-header";
import { PageSection } from "@/components/ui/page-section";
import { StatusBadge } from "@/components/ui/status-badge";
import { SystemBanner } from "@/components/ui/system-banner";
import {
  getApiErrorMessage,
  getAgentRuntimeStatus,
  listAgentProviders,
  listAgentRuns,
  toApiResult,
} from "@/lib/api";
import type { AgentProviderSetting, AgentRun, AgentRunStatus, AgentRuntimeStatus } from "@/lib/api";
import {
  cancelAgentRunAction,
  retryAgentRunAction,
  setAgentDecisionStatusAction,
  startProfileBuilderAgentAction,
  updateAgentProviderAction,
} from "./actions";

type AgentsPageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

const TOOL_POLICIES = ["read_only", "workspace_write", "safe_shell", "network_tools", "external_action"];
const AGENT_TYPES = ["profile_builder", "match_review", "search_strategy", "application_prep", "follow_up"];

export default async function AgentsPage({ searchParams }: AgentsPageProps) {
  const params = await searchParams;
  const notice = getSearchParam(params, "agent_notice");
  const error = getSearchParam(params, "agent_error");
  const selectedRunId = Number(getSearchParam(params, "agent_run_id"));
  const [providersResult, runsResult, runtimeResult] = await Promise.all([
    toApiResult(listAgentProviders()),
    toApiResult(listAgentRuns({ limit: 30 })),
    toApiResult(getAgentRuntimeStatus()),
  ]);

  const providers = providersResult.ok ? providersResult.data.results : [];
  const runs = runsResult.ok ? runsResult.data.results : [];
  const runtime = runtimeResult.ok ? runtimeResult.data : null;
  const latestRun = runs[0] ?? null;
  const selectedRun =
    (Number.isInteger(selectedRunId)
      ? runs.find((run) => run.id === selectedRunId)
      : undefined) ?? latestRun;
  const successfulRuns = runs.filter((run) => run.status === "success").length;
  const failedRuns = runs.filter((run) => run.status === "failed").length;
  const workerOnlyProviders = providers.filter((provider) => provider.worker_only).length;

  return (
    <div className="space-y-4">
      <PageHeader
        title="Agents"
        eyebrow="Orchestrator"
        description="Runtime settings, local agent runs, permissions, artifacts, and audit history."
        actions={<StartRunForm providers={providers} />}
      />

      {notice ? <SystemBanner tone="success">{notice}</SystemBanner> : null}

      {error ? <ErrorState title="Agent action failed" message={error} /> : null}

      {!providersResult.ok || !runsResult.ok || !runtimeResult.ok ? (
        <ErrorState
          title="Backend API is unavailable"
          message="Agent settings, runtime status, or run history could not be loaded."
          detail={[
            providersResult.ok ? "" : getApiErrorMessage(providersResult.error),
            runsResult.ok ? "" : getApiErrorMessage(runsResult.error),
            runtimeResult.ok ? "" : getApiErrorMessage(runtimeResult.error),
          ]
            .filter(Boolean)
            .join("\n")}
        />
      ) : null}

      <div className="grid gap-3 md:grid-cols-4">
        <MetricCard label="Runs" value={runs.length} detail={latestRun ? `Latest: ${labelize(latestRun.status)}` : "No runs yet"} />
        <MetricCard label="Succeeded" value={successfulRuns} detail="Completed reviews" />
        <MetricCard label="Failed" value={failedRuns} detail="Needs attention" />
        <MetricCard label="Queued" value={runtime?.queued_runs ?? 0} detail={`${workerOnlyProviders} worker-only providers`} />
      </div>

      {runtime ? <RuntimeStatusPanel runtime={runtime} /> : null}

      <div className="grid min-w-0 gap-4 xl:grid-cols-[380px_minmax(0,1fr)_420px]">
        <RunHistoryPanel runs={runs} selectedRun={selectedRun} />
        <AgentRunDetailDrawer run={selectedRun} />
        <ProviderSettingsPanel providers={providers} />
      </div>
    </div>
  );
}

function StartRunForm({ providers }: { providers: AgentProviderSetting[] }) {
  const defaultProvider = providers.find((provider) => provider.provider === "direct_api") ?? providers[0];

  return (
    <form action={startProfileBuilderAgentAction} className="flex flex-wrap items-center justify-end gap-2">
      <Select
        name="agent_type"
        defaultValue="profile_builder"
        className="mt-0"
      >
        {AGENT_TYPES.map((agentType) => (
          <option key={agentType} value={agentType}>
            {labelize(agentType)}
          </option>
        ))}
      </Select>
      <Select
        name="provider"
        defaultValue={defaultProvider?.provider ?? "direct_api"}
        className="mt-0"
      >
        {providers.length ? (
          providers.map((provider) => (
            <option key={provider.provider} value={provider.provider}>
              {provider.label}
            </option>
          ))
        ) : (
          <option value="direct_api">Direct API</option>
        )}
      </Select>
      <Input
        name="model_name"
        placeholder="Model"
        className="mt-0 w-36"
      />
      <Select
        name="tool_policy"
        defaultValue={defaultProvider?.default_tool_policy ?? "read_only"}
        className="mt-0"
      >
        {TOOL_POLICIES.map((policy) => (
          <option key={policy} value={policy}>
            {labelize(policy)}
          </option>
        ))}
      </Select>
      <label className="flex h-9 items-center gap-2 rounded-md border border-[var(--border)] bg-[var(--surface-recessed)] px-2 text-xs font-semibold text-[var(--muted)]">
        <input type="checkbox" name="user_consent" className="h-4 w-4 rounded border-slate-300 text-slate-950" />
        Consent
      </label>
      <Button type="submit" variant="primary">
        Run Agent
      </Button>
    </form>
  );
}

function RuntimeStatusPanel({ runtime }: { runtime: AgentRuntimeStatus }) {
  return (
    <PageSection
      title="Runtime controls"
      actions={
        <div className="flex flex-wrap gap-2">
          <StatusBadge tone={runtime.execution_mode === "queued" ? "warning" : "info"} withDot>
            {labelize(runtime.execution_mode)}
          </StatusBadge>
          <StatusBadge tone="neutral">Batch {runtime.queue_batch_size}</StatusBadge>
          <StatusBadge tone={runtime.running_runs ? "warning" : "neutral"}>{runtime.running_runs} running</StatusBadge>
        </div>
      }
    >
      <div className="grid gap-3 p-4 lg:grid-cols-3">
        {runtime.providers.map((provider) => (
          <div key={provider.provider} className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
            <div className="flex items-start justify-between gap-2">
              <div className="text-sm font-semibold text-slate-900">{provider.label}</div>
              <StatusBadge tone={provider.consent_required ? "warning" : "neutral"}>
                {provider.consent_required ? "Consent" : "No consent"}
              </StatusBadge>
            </div>
            <div className="mt-2 grid gap-1 text-xs text-slate-600">
              <span>Daily: {provider.daily_runs_used}/{provider.daily_run_limit}</span>
              <span>Budget: ${provider.monthly_spend_estimate.toFixed(2)} / ${provider.monthly_budget_estimate.toFixed(2)}</span>
              <span>Estimate/run: {(provider.estimated_cost_per_run_cents / 100).toFixed(2)} USD</span>
            </div>
          </div>
        ))}
      </div>
    </PageSection>
  );
}

function ProviderSettingsPanel({ providers }: { providers: AgentProviderSetting[] }) {
  return (
    <PageSection title="Provider settings">
      {providers.length === 0 ? (
        <div className="px-4 py-5 text-sm text-slate-600">Provider settings are unavailable.</div>
      ) : (
        <div className="divide-y divide-slate-100">
          {providers.map((provider) => (
            <form key={provider.provider} action={updateAgentProviderAction} className="space-y-3 px-4 py-3">
              <input type="hidden" name="provider" value={provider.provider} />
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="text-sm font-semibold text-slate-950">{provider.label}</h3>
                  <div className="mt-1 flex flex-wrap gap-2">
                    <StatusBadge tone={provider.enabled ? "success" : "neutral"} withDot>
                      {provider.enabled ? "Enabled" : "Disabled"}
                    </StatusBadge>
                    {provider.worker_only ? <StatusBadge tone="warning">Worker-only</StatusBadge> : null}
                    <StatusBadge tone={provider.api_key_configured ? "success" : "neutral"}>
                      {provider.api_key_env_var ? `${provider.api_key_env_var}: ${provider.api_key_configured ? "set" : "missing"}` : "No key"}
                    </StatusBadge>
                  </div>
                </div>
                <label className="flex h-8 items-center gap-2 text-xs font-semibold text-slate-700">
                  <input
                    type="checkbox"
                    name="enabled"
                    defaultChecked={provider.enabled}
                    className="h-4 w-4 rounded border-slate-300 text-slate-950"
                  />
                  Enabled
                </label>
                <label className="flex h-8 items-center gap-2 text-xs font-semibold text-slate-700">
                  <input
                    type="checkbox"
                    name="consent_required"
                    defaultChecked={provider.consent_required}
                    className="h-4 w-4 rounded border-slate-300 text-slate-950"
                  />
                  Consent required
                </label>
              </div>
              <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_160px]">
                <label className="block">
                  <span className="text-xs font-medium text-slate-600">Model</span>
                  <Input
                    name="model_name"
                    defaultValue={provider.model_name}
                  />
                </label>
                <label className="block">
                  <span className="text-xs font-medium text-slate-600">Policy</span>
                  <Select
                    name="default_tool_policy"
                    defaultValue={provider.default_tool_policy}
                  >
                    {TOOL_POLICIES.map((policy) => (
                      <option key={policy} value={policy}>
                        {labelize(policy)}
                      </option>
                    ))}
                  </Select>
                </label>
              </div>
              <div className="grid gap-2 sm:grid-cols-3">
                <NumberInput label="Daily limit" name="daily_run_limit" defaultValue={provider.daily_run_limit} />
                <NumberInput label="Monthly cents" name="monthly_budget_cents" defaultValue={provider.monthly_budget_cents} />
                <NumberInput label="Estimate cents/run" name="estimated_cost_per_run_cents" defaultValue={provider.estimated_cost_per_run_cents} />
              </div>
              <label className="block">
                <span className="text-xs font-medium text-slate-600">Notes</span>
                <Textarea
                  name="notes"
                  defaultValue={provider.notes}
                  rows={2}
                />
              </label>
              <div className="flex justify-end">
                <Button type="submit" size="sm">
                  Save provider
                </Button>
              </div>
            </form>
          ))}
        </div>
      )}
    </PageSection>
  );
}

function RunHistoryPanel({
  runs,
  selectedRun,
}: {
  runs: AgentRun[];
  selectedRun: AgentRun | null;
}) {
  return (
    <section className="min-w-0 rounded-lg border border-slate-200 bg-white">
      <div className="border-b border-slate-200 px-4 py-3">
        <h2 className="text-sm font-semibold text-slate-950">Run history</h2>
      </div>
      {runs.length === 0 ? (
        <div className="px-4 py-5 text-sm text-slate-600">No agent runs yet.</div>
      ) : (
        <div className="divide-y divide-slate-100">
          {runs.map((run) => (
            <Link
              key={run.id}
              href={`/agents?agent_run_id=${run.id}`}
              className={[
                "block border-l-2 px-4 py-4 transition hover:bg-slate-800",
                run.id === selectedRun?.id ? "border-indigo-300 bg-indigo-500/10" : "border-transparent",
              ].join(" ")}
            >
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="text-sm font-semibold text-slate-950">
                  #{run.id} {labelize(run.agent_type)}
                </h3>
                <StatusBadge tone={statusTone(run.status)} withDot>
                  {labelize(run.status)}
                </StatusBadge>
              </div>
              <p className="mt-2 line-clamp-2 text-sm leading-6 text-slate-600">
                {run.result_summary || run.user_safe_error || "Run is waiting for output."}
              </p>
              <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 font-mono text-[11px] text-slate-500">
                <span>{run.provider}</span>
                <span>{labelize(run.tool_policy)}</span>
                <span>{formatDate(run.requested_at)}</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}

function AgentRunDetailDrawer({ run }: { run: AgentRun | null }) {
  if (!run) {
    return (
      <DetailDrawer title="No run selected" subtitle="Start or select an agent run.">
        <p className="text-sm leading-6 text-slate-500">
          Execution logs, permissions, artifacts, approval decisions, and audit history will appear here.
        </p>
      </DetailDrawer>
    );
  }

  return (
    <DetailDrawer
      eyebrow={`Run / ${run.id}`}
      title={labelize(run.agent_type)}
      subtitle={`${run.provider} - ${run.model_name || "model not recorded"}`}
      closeHref="/agents"
      footer={
        <div className="flex justify-end gap-2">
          {run.status === "queued" || run.status === "running" || run.status === "waiting_approval" ? (
            <form action={cancelAgentRunAction}>
              <input type="hidden" name="run_id" value={run.id} />
              <Button type="submit">
                Cancel
              </Button>
            </form>
          ) : null}
          <form action={retryAgentRunAction}>
            <input type="hidden" name="run_id" value={run.id} />
            <Button type="submit" variant="primary">
              Retry
            </Button>
          </form>
        </div>
      }
    >
      <div className="space-y-4">
        <div className="flex flex-wrap gap-2">
          <StatusBadge tone={statusTone(run.status)} withDot>{labelize(run.status)}</StatusBadge>
          <StatusBadge tone="info">{run.provider}</StatusBadge>
          <StatusBadge tone="neutral">{labelize(run.tool_policy)}</StatusBadge>
        </div>
        <p className="rounded-lg border border-slate-800 bg-slate-950 p-4 text-sm leading-6 text-slate-300">
          {run.result_summary || run.user_safe_error || "Run is waiting for output."}
        </p>
        <div className="grid gap-3 lg:grid-cols-2">
          <StepsPanel run={run} />
          <PermissionsPanel run={run} />
        </div>
        <RuntimePanel run={run} />
        <DecisionsPanel run={run} />
        <ArtifactsPanel run={run} />
        <AuditPanel run={run} />
      </div>
    </DetailDrawer>
  );
}

function NumberInput({
  label,
  name,
  defaultValue,
}: {
  label: string;
  name: string;
  defaultValue: number;
}) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-slate-600">{label}</span>
      <Input
        name={name}
        type="number"
        min={0}
        defaultValue={defaultValue}
      />
    </label>
  );
}

function StepsPanel({ run }: { run: AgentRun }) {
  return (
    <div className="rounded-md border border-slate-200">
      <div className="border-b border-slate-200 px-3 py-2 text-xs font-semibold uppercase tracking-normal text-slate-500">
        Steps
      </div>
      <div className="divide-y divide-slate-100">
        {run.steps.length ? (
          run.steps.map((step) => (
            <div key={step.id} className="px-3 py-2">
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm font-medium text-slate-800">{step.order}. {step.name}</span>
                <StatusBadge tone={statusTone(step.status)}>{labelize(step.status)}</StatusBadge>
              </div>
              {step.message ? <p className="mt-1 text-xs leading-5 text-slate-500">{step.message}</p> : null}
            </div>
          ))
        ) : (
          <div className="px-3 py-3 text-sm text-slate-600">No steps recorded.</div>
        )}
      </div>
    </div>
  );
}

function PermissionsPanel({ run }: { run: AgentRun }) {
  return (
    <div className="rounded-md border border-slate-200">
      <div className="border-b border-slate-200 px-3 py-2 text-xs font-semibold uppercase tracking-normal text-slate-500">
        Permissions
      </div>
      <div className="divide-y divide-slate-100">
        {run.permissions.length ? (
          run.permissions.map((permission) => (
            <div key={permission.id} className="px-3 py-2">
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm font-medium text-slate-800">{labelize(permission.policy_level)}</span>
                <StatusBadge tone={permission.status === "granted" ? "success" : "warning"}>
                  {labelize(permission.status)}
                </StatusBadge>
              </div>
              <p className="mt-1 text-xs leading-5 text-slate-500">{permission.reason}</p>
            </div>
          ))
        ) : (
          <div className="px-3 py-3 text-sm text-slate-600">No permissions recorded.</div>
        )}
      </div>
    </div>
  );
}

function RuntimePanel({ run }: { run: AgentRun }) {
  if (!run.runtime_invocations.length) {
    return null;
  }

  return (
    <div className="rounded-md border border-slate-200">
      <div className="border-b border-slate-200 px-3 py-2 text-xs font-semibold uppercase tracking-normal text-slate-500">
        Runtime invocations
      </div>
      <div className="divide-y divide-slate-100">
        {run.runtime_invocations.map((invocation) => (
          <div key={invocation.id} className="grid gap-2 px-3 py-2 md:grid-cols-[180px_minmax(0,1fr)]">
            <div>
              <div className="text-sm font-medium text-slate-800">{invocation.adapter}</div>
              <div className="mt-1 flex flex-wrap gap-2">
                <StatusBadge tone={runtimeTone(invocation.status)}>{labelize(invocation.status)}</StatusBadge>
                <StatusBadge tone="info">{invocation.provider}</StatusBadge>
              </div>
            </div>
            <pre className="max-h-44 overflow-auto rounded-md bg-slate-950 px-3 py-2 text-xs leading-5 text-slate-50">
              {formatJson(invocation.output_snapshot)}
            </pre>
          </div>
        ))}
      </div>
    </div>
  );
}

function ArtifactsPanel({ run }: { run: AgentRun }) {
  if (!run.artifacts.length) {
    return null;
  }

  return (
    <div className="rounded-md border border-slate-200">
      <div className="border-b border-slate-200 px-3 py-2 text-xs font-semibold uppercase tracking-normal text-slate-500">
        Artifacts
      </div>
      <div className="divide-y divide-slate-100">
        {run.artifacts.map((artifact) => (
          <div key={artifact.id} className="px-3 py-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h4 className="text-sm font-semibold text-slate-900">{artifact.title}</h4>
              <StatusBadge>{artifact.artifact_type}</StatusBadge>
            </div>
            {artifact.content ? (
              <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap rounded-md bg-slate-950 px-3 py-2 text-xs leading-5 text-slate-50">
                {artifact.content}
              </pre>
            ) : null}
            {Object.keys(artifact.metadata).length ? (
              <pre className="mt-2 max-h-40 overflow-auto rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-xs leading-5 text-slate-700">
                {formatJson(artifact.metadata)}
              </pre>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
}

function DecisionsPanel({ run }: { run: AgentRun }) {
  if (!run.decisions.length) {
    return null;
  }

  return (
    <div className="rounded-md border border-slate-200">
      <div className="border-b border-slate-200 px-3 py-2 text-xs font-semibold uppercase tracking-normal text-slate-500">
        Approval queue
      </div>
      <div className="divide-y divide-slate-100">
        {run.decisions.map((decision) => (
          <div key={decision.id} className="grid gap-3 px-3 py-3 md:grid-cols-[minmax(0,1fr)_auto]">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h4 className="text-sm font-semibold text-slate-900">{labelize(decision.decision_type)}</h4>
                <StatusBadge tone={decision.status === "pending" ? "warning" : decision.status === "approved" ? "success" : "neutral"}>
                  {labelize(decision.status)}
                </StatusBadge>
              </div>
              <p className="mt-1 text-sm leading-6 text-slate-600">{decision.question}</p>
              <pre className="mt-2 max-h-40 overflow-auto rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-xs leading-5 text-slate-700">
                {formatJson(decision.proposed_changes)}
              </pre>
            </div>
            {decision.status === "pending" ? (
              <div className="flex items-start gap-2">
                <form action={setAgentDecisionStatusAction}>
                  <input type="hidden" name="decision_id" value={decision.id} />
                  <input type="hidden" name="status" value="approved" />
                  <Button
                    type="submit"
                    variant="primary"
                    size="sm"
                  >
                    Accept
                  </Button>
                </form>
                <form action={setAgentDecisionStatusAction}>
                  <input type="hidden" name="decision_id" value={decision.id} />
                  <input type="hidden" name="status" value="rejected" />
                  <Button type="submit" size="sm">
                    Reject
                  </Button>
                </form>
              </div>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
}

function AuditPanel({ run }: { run: AgentRun }) {
  if (!run.audit_logs.length) {
    return null;
  }

  return (
    <details className="rounded-md border border-slate-200">
      <summary className="cursor-pointer px-3 py-2 text-xs font-semibold uppercase tracking-normal text-slate-500">
        Audit logs
      </summary>
      <div className="divide-y divide-slate-100 border-t border-slate-200">
        {run.audit_logs.map((log) => (
          <div key={log.id} className="px-3 py-2 text-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-medium text-slate-800">{labelize(log.event_type)}</span>
              <span className="text-xs text-slate-500">{formatDate(log.created_at)}</span>
            </div>
            {log.message ? <p className="mt-1 text-xs leading-5 text-slate-500">{log.message}</p> : null}
          </div>
        ))}
      </div>
    </details>
  );
}

function getSearchParam(params: Record<string, string | string[] | undefined>, key: string) {
  const value = params[key];
  return Array.isArray(value) ? value[0] : value;
}

function labelize(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function statusTone(status: AgentRunStatus) {
  if (status === "success") return "success";
  if (status === "failed" || status === "cancelled") return "danger";
  if (status === "running" || status === "waiting_approval") return "warning";
  return "neutral";
}

function runtimeTone(status: string) {
  if (status === "success") return "success";
  if (status === "failed") return "danger";
  if (status === "skipped") return "warning";
  return "neutral";
}

function formatDate(value: string | null) {
  if (!value) {
    return "Not recorded";
  }

  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatJson(value: unknown) {
  return JSON.stringify(value ?? {}, null, 2);
}
