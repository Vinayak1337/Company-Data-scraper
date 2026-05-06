"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import {
  getApiErrorMessage,
  updateAgentProvider,
  updateNotificationPreferences,
} from "@/lib/api";

export async function updateNotificationPreferencesAction(formData: FormData) {
  try {
    await updateNotificationPreferences({
      email_address: getFormValue(formData, "email_address"),
      immediate_email_enabled: getFormBool(formData, "immediate_email_enabled"),
      quiet_hours_enabled: getFormBool(formData, "quiet_hours_enabled"),
      quiet_hours_start: getFormValue(formData, "quiet_hours_start") || "22:00",
      quiet_hours_end: getFormValue(formData, "quiet_hours_end") || "08:00",
      timezone: getFormValue(formData, "timezone") || "UTC",
      digest_enabled: getFormBool(formData, "digest_enabled"),
      digest_frequency: getFormValue(formData, "digest_frequency") || "daily",
      digest_time: getFormValue(formData, "digest_time") || "09:00",
      digest_channel: getFormValue(formData, "digest_channel") || "email",
      minimum_match_score: Number(getFormValue(formData, "minimum_match_score") || "75"),
      minimum_confidence_score: Number(getFormValue(formData, "minimum_confidence_score") || "55"),
      max_digest_items: Number(getFormValue(formData, "max_digest_items") || "10"),
    });
    revalidatePath("/settings");
    revalidatePath("/");
  } catch (error) {
    redirectWithSettingsError(getApiErrorMessage(error));
  }

  redirect("/settings?settings_notice=Notification%20preferences%20updated.");
}

export async function updateAgentProviderAction(formData: FormData) {
  const provider = getFormValue(formData, "provider");
  if (!provider) {
    redirectWithSettingsError("Provider is required.");
  }

  try {
    await updateAgentProvider(provider, {
      enabled: getFormBool(formData, "enabled"),
      model_name: getFormValue(formData, "model_name"),
      api_key_env_var: getFormValue(formData, "api_key_env_var"),
      daily_run_limit: Number(getFormValue(formData, "daily_run_limit") || "25"),
      consent_required: getFormBool(formData, "consent_required"),
    });
    revalidatePath("/settings");
    revalidatePath("/");
  } catch (error) {
    redirectWithSettingsError(getApiErrorMessage(error));
  }

  redirect("/settings?settings_notice=AI%20provider%20updated.");
}

function getFormValue(formData: FormData, key: string) {
  const value = formData.get(key);
  return typeof value === "string" ? value.trim() : "";
}

function getFormBool(formData: FormData, key: string) {
  const value = formData.get(key);
  return typeof value === "string" && ["1", "true", "yes", "on"].includes(value.trim().toLowerCase());
}

function redirectWithSettingsError(message: string): never {
  redirect(`/settings?settings_error=${encodeURIComponent(message)}`);
}
