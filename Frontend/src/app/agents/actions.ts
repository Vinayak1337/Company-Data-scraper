"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import {
  cancelAgentRun,
  getApiErrorMessage,
  retryAgentRun,
  setAgentDecisionStatus,
  startAgentRun,
  updateAgentProvider,
} from "@/lib/api";
import type { AgentProvider, AgentToolPolicy } from "@/lib/api";

export async function startProfileBuilderAgentAction(formData: FormData) {
  try {
    await startAgentRun({
      agent_type: getFormValue(formData, "agent_type") || "profile_builder",
      provider: getFormValue(formData, "provider") || "direct_api",
      model_name: getFormValue(formData, "model_name"),
      tool_policy: getFormValue(formData, "tool_policy"),
      user_consent: formData.get("user_consent") === "on",
    });
    revalidatePath("/agents");
  } catch (error) {
    redirectWithAgentError(getApiErrorMessage(error));
  }

  redirect("/agents?agent_notice=Agent%20run%20created.");
}

export async function updateAgentProviderAction(formData: FormData) {
  const provider = getFormValue(formData, "provider") as AgentProvider;

  if (!provider) {
    redirectWithAgentError("Provider is required.");
  }

  try {
    await updateAgentProvider(provider, {
      enabled: formData.get("enabled") === "on",
      model_name: getFormValue(formData, "model_name"),
      default_tool_policy: getFormValue(formData, "default_tool_policy") as AgentToolPolicy,
      consent_required: formData.get("consent_required") === "on",
      daily_run_limit: getNumberValue(formData, "daily_run_limit"),
      monthly_budget_cents: getNumberValue(formData, "monthly_budget_cents"),
      estimated_cost_per_run_cents: getNumberValue(formData, "estimated_cost_per_run_cents"),
      notes: getFormValue(formData, "notes"),
    });
    revalidatePath("/agents");
  } catch (error) {
    redirectWithAgentError(getApiErrorMessage(error));
  }

  redirect("/agents?agent_notice=Provider%20settings%20updated.");
}

export async function cancelAgentRunAction(formData: FormData) {
  const runId = getRunId(formData);

  try {
    await cancelAgentRun(runId);
    revalidatePath("/agents");
  } catch (error) {
    redirectWithAgentError(getApiErrorMessage(error));
  }

  redirect("/agents?agent_notice=Agent%20run%20cancelled.");
}

export async function retryAgentRunAction(formData: FormData) {
  const runId = getRunId(formData);

  try {
    await retryAgentRun(runId);
    revalidatePath("/agents");
  } catch (error) {
    redirectWithAgentError(getApiErrorMessage(error));
  }

  redirect("/agents?agent_notice=Agent%20run%20retried.");
}

export async function setAgentDecisionStatusAction(formData: FormData) {
  const decisionId = Number(getFormValue(formData, "decision_id"));
  const status = getFormValue(formData, "status");

  if (!Number.isInteger(decisionId) || decisionId <= 0) {
    redirectWithAgentError("A valid decision ID is required.");
  }

  if (status !== "approved" && status !== "rejected") {
    redirectWithAgentError("Decision status must be approved or rejected.");
  }

  try {
    await setAgentDecisionStatus(decisionId, status);
    revalidatePath("/agents");
  } catch (error) {
    redirectWithAgentError(getApiErrorMessage(error));
  }

  redirect(`/agents?agent_notice=Decision%20${status}.`);
}

function getRunId(formData: FormData) {
  const runId = Number(getFormValue(formData, "run_id"));

  if (!Number.isInteger(runId) || runId <= 0) {
    redirectWithAgentError("A valid agent run ID is required.");
  }

  return runId;
}

function getFormValue(formData: FormData, key: string) {
  const value = formData.get(key);
  return typeof value === "string" ? value.trim() : "";
}

function getNumberValue(formData: FormData, key: string) {
  const value = Number(getFormValue(formData, key));
  return Number.isFinite(value) && value >= 0 ? value : 0;
}

function redirectWithAgentError(message: string): never {
  redirect(`/agents?agent_error=${encodeURIComponent(message)}`);
}
