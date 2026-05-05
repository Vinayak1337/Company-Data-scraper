"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import {
  ApiError,
  createCompany,
  deleteAllPersonalData,
  getApiErrorMessage,
  importCompanyWatchlist,
  importWorkspaceData,
  updateNotificationPreferences,
} from "@/lib/api";
import type {
  CompanyImportCompany,
  CompanyImportPayload,
  CompanyImportResult,
  PriorityTier,
  WorkModeFilter,
} from "@/lib/api";

export async function importCompanyWatchlistAction(formData: FormData) {
  const rawJson = getFormValue(formData, "import_json");

  if (!rawJson) {
    redirectWithSettingsError("Paste company watchlist JSON before importing.");
  }

  let payload: CompanyImportPayload;

  try {
    payload = JSON.parse(rawJson) as CompanyImportPayload;
  } catch {
    redirectWithSettingsError("Import JSON is invalid.");
  }

  let result: CompanyImportResult;

  try {
    result = await importCompanyWatchlist(payload);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      try {
        result = await importByCreatingCompanies(payload);
      } catch (fallbackError) {
        redirectWithSettingsError(getApiErrorMessage(fallbackError));
      }
    } else {
      redirectWithSettingsError(getApiErrorMessage(error));
    }
  }

  revalidatePath("/companies");
  revalidatePath("/settings");

  const message = formatImportResult(result);
  redirect(`/settings?settings_notice=${encodeURIComponent(message)}`);
}

export async function updateNotificationPreferencesAction(formData: FormData) {
  try {
    await updateNotificationPreferences({
      quiet_hours_enabled: formData.get("quiet_hours_enabled") === "on",
      quiet_hours_start: getFormValue(formData, "quiet_hours_start"),
      quiet_hours_end: getFormValue(formData, "quiet_hours_end"),
      timezone: getFormValue(formData, "timezone") || "UTC",
      digest_enabled: formData.get("digest_enabled") === "on",
      digest_frequency: getFormValue(formData, "digest_frequency") || "daily",
      digest_time: getFormValue(formData, "digest_time"),
      digest_channel: getFormValue(formData, "digest_channel") || "local",
    });
    revalidatePath("/settings");
  } catch (error) {
    redirectWithSettingsError(getApiErrorMessage(error));
  }

  redirect("/settings?settings_notice=Notification%20preferences%20updated.");
}

export async function importWorkspaceAction(formData: FormData) {
  const rawJson = getFormValue(formData, "workspace_json");

  if (!rawJson) {
    redirectWithSettingsError("Paste workspace export JSON before importing.");
  }

  let payload: Record<string, unknown>;
  try {
    payload = JSON.parse(rawJson) as Record<string, unknown>;
  } catch {
    redirectWithSettingsError("Workspace import JSON is invalid.");
  }

  try {
    const result = await importWorkspaceData(payload);
    revalidatePath("/");
    revalidatePath("/companies");
    revalidatePath("/jobs");
    revalidatePath("/profile");
    revalidatePath("/applications");
    revalidatePath("/agents");
    revalidatePath("/analytics");
    revalidatePath("/settings");
    redirect(
      `/settings?settings_notice=${encodeURIComponent(
        `Workspace import ${result.status}: ${sumCounts(result.imported)} records processed, ${result.error_count} errors.`,
      )}`,
    );
  } catch (error) {
    redirectWithSettingsError(getApiErrorMessage(error));
  }
}

export async function deleteAllPersonalDataAction(formData: FormData) {
  const confirmation = getFormValue(formData, "delete_confirmation");

  try {
    const result = await deleteAllPersonalData(confirmation);
    revalidatePath("/");
    revalidatePath("/companies");
    revalidatePath("/jobs");
    revalidatePath("/profile");
    revalidatePath("/applications");
    revalidatePath("/agents");
    revalidatePath("/analytics");
    revalidatePath("/settings");
    redirect(
      `/settings?settings_notice=${encodeURIComponent(
        `Personal data deleted: ${sumCounts(result.deleted)} records removed.`,
      )}`,
    );
  } catch (error) {
    redirectWithSettingsError(getApiErrorMessage(error));
  }
}

async function importByCreatingCompanies(
  payload: CompanyImportPayload,
): Promise<CompanyImportResult> {
  const companies = extractCompanies(payload);

  if (companies.length === 0) {
    throw new Error(
      "Import JSON must include a companies, watchlist, or company_watchlist array.",
    );
  }

  const errors: NonNullable<CompanyImportResult["errors"]> = [];
  let created = 0;

  for (const [index, company] of companies.entries()) {
    if (!company.careers_url) {
      errors.push({
        index,
        company: company.name,
        error: "careers_url is required",
      });
      continue;
    }

    try {
      await createCompany(company);
      created += 1;
    } catch (error) {
      errors.push({
        index,
        company: company.name,
        careers_url: company.careers_url,
        error: getApiErrorMessage(error),
      });
    }
  }

  return {
    created_count: created,
    updated_count: 0,
    skipped: errors.length,
    errors,
    message:
      "Backend import endpoint unavailable; imported through the company create endpoint.",
  };
}

function extractCompanies(payload: CompanyImportPayload): CompanyImportCompany[] {
  const source = Array.isArray(payload)
    ? payload
    : firstArray(
        payload.companies,
        payload.watchlist,
        payload.company_watchlist,
      );

  return source.map(normalizeCompany).filter(isCompanyImportCompany);
}

function normalizeCompany(value: CompanyImportCompany | unknown): CompanyImportCompany | null {
  if (!isRecord(value)) {
    return null;
  }

  const careersUrl = getStringValue(value, ["careers_url", "url", "source_url"]);

  return {
    name: getStringValue(value, ["name", "company", "company_name"]),
    careers_url: careersUrl,
    priority_tier: getStringValue(value, [
      "priority_tier",
      "priority",
    ]) as PriorityTier,
    title_keywords: getKeywordArray(value.title_keywords),
    negative_title_keywords: getKeywordArray(value.negative_title_keywords),
    location_keywords: getKeywordArray(value.location_keywords),
    work_mode_filter: getStringValue(value, [
      "work_mode_filter",
      "work_mode",
      "remote_policy",
    ]) as WorkModeFilter,
  };
}

function isCompanyImportCompany(
  value: CompanyImportCompany | null,
): value is CompanyImportCompany {
  return value !== null;
}

function firstArray(
  ...values: Array<CompanyImportCompany[] | undefined>
): CompanyImportCompany[] {
  return values.find((value) => Array.isArray(value)) ?? [];
}

function getKeywordArray(value: unknown) {
  if (Array.isArray(value)) {
    return value.map(String).map((item) => item.trim()).filter(Boolean);
  }

  if (typeof value === "string") {
    return value
      .split(/[\n,]/)
      .map((item) => item.trim())
      .filter(Boolean);
  }

  return [];
}

function getStringValue(record: Record<string, unknown>, keys: string[]) {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "string") {
      return value.trim();
    }
  }

  return "";
}

function getFormValue(formData: FormData, key: string) {
  const value = formData.get(key);
  return typeof value === "string" ? value.trim() : "";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function formatImportResult(result: CompanyImportResult) {
  const created = getResultCount(result.created_count, result.created);
  const updated = getResultCount(result.updated_count, result.updated);
  const skipped = result.skipped ?? 0;
  const errorCount = result.error_count ?? result.errors?.length ?? 0;

  return [
    `Import finished: ${created} created`,
    `${updated} updated`,
    `${skipped} skipped`,
    `${errorCount} errors`,
  ].join(", ");
}

function getResultCount(preferred: number | undefined, fallback: unknown) {
  if (typeof preferred === "number") {
    return preferred;
  }

  if (typeof fallback === "number") {
    return fallback;
  }

  if (Array.isArray(fallback)) {
    return fallback.length;
  }

  return 0;
}

function sumCounts(counts: Record<string, number>) {
  return Object.values(counts).reduce((sum, value) => sum + value, 0);
}

function redirectWithSettingsError(message: string): never {
  redirect(`/settings?settings_error=${encodeURIComponent(message)}`);
}
