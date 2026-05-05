"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import {
  createCompany,
  deleteCompany,
  generateCompanyIntelligence,
  getApiErrorMessage,
  pauseCompany,
  resumeCompany,
  scrapeCompany,
  updateCompany,
} from "@/lib/api";

export async function addCompanyAction(formData: FormData) {
  const careersUrl = getFormValue(formData, "careers_url");
  const name = getFormValue(formData, "name");
  const priorityTier = getFormValue(formData, "priority_tier") || "normal";

  if (!careersUrl) {
    redirectWithCompanyError("Careers URL is required.");
  }

  try {
    new URL(careersUrl);
  } catch {
    redirectWithCompanyError("Enter a valid careers URL.");
  }

  try {
    await createCompany({
      careers_url: careersUrl,
      name: name || undefined,
      priority_tier: priorityTier,
    });
    revalidatePath("/companies");
  } catch (error) {
    redirectWithCompanyError(getApiErrorMessage(error));
  }

  redirect("/companies?company_added=1");
}

export async function scrapeCompanyAction(formData: FormData) {
  const companyId = Number(getFormValue(formData, "company_id"));

  if (!Number.isInteger(companyId) || companyId <= 0) {
    redirectWithCompanyError("A valid company ID is required to scan.");
  }

  let result;

  try {
    result = await scrapeCompany(companyId);
    revalidatePath("/companies");
  } catch (error) {
    redirectWithCompanyError(getApiErrorMessage(error));
  }

  const message = [
    `scan_status=${encodeURIComponent(result.status)}`,
    `jobs_found=${encodeURIComponent(String(result.jobs_found))}`,
    `jobs_created=${encodeURIComponent(String(result.jobs_created))}`,
    `jobs_updated=${encodeURIComponent(String(result.jobs_updated))}`,
  ].join("&");

  redirect(`/companies?${message}`);
}

export async function updateCompanyAction(formData: FormData) {
  const companyId = getCompanyId(formData);
  const name = getFormValue(formData, "name");
  const priorityTier = getFormValue(formData, "priority_tier") || "normal";
  const workModeFilter = getFormValue(formData, "work_mode_filter");
  const scanFrequencyHours = Number(getFormValue(formData, "scan_frequency_hours") || "24");
  const alertNewRoles = getFormValue(formData, "alert_new_roles") === "on";

  try {
    await updateCompany(companyId, {
      name,
      priority_tier: priorityTier,
      title_keywords: getKeywordList(formData, "title_keywords"),
      negative_title_keywords: getKeywordList(
        formData,
        "negative_title_keywords",
      ),
      location_keywords: getKeywordList(formData, "location_keywords"),
      work_mode_filter: workModeFilter,
      scan_frequency_hours:
        Number.isInteger(scanFrequencyHours) && scanFrequencyHours > 0
          ? scanFrequencyHours
          : 24,
      alert_new_roles: alertNewRoles,
    });
    revalidatePath("/companies");
  } catch (error) {
    redirectWithCompanyError(getApiErrorMessage(error));
  }

  redirect("/companies?company_updated=1");
}

export async function toggleCompanyPausedAction(formData: FormData) {
  const companyId = getCompanyId(formData);
  const operation = getFormValue(formData, "operation");
  let redirectPath = "";

  try {
    if (operation === "pause") {
      await pauseCompany(companyId);
      revalidatePath("/companies");
      redirectPath = "/companies?company_paused=1";
    }

    if (operation === "resume") {
      await resumeCompany(companyId);
      revalidatePath("/companies");
      redirectPath = "/companies?company_resumed=1";
    }
  } catch (error) {
    redirectWithCompanyError(getApiErrorMessage(error));
  }

  if (!redirectPath) {
    redirectWithCompanyError("Choose pause or resume for the company action.");
  }

  redirect(redirectPath);
}

export async function deleteCompanyAction(formData: FormData) {
  const companyId = getCompanyId(formData);
  const confirmation = getFormValue(formData, "delete_confirm");

  if (confirmation !== "DELETE") {
    redirectWithCompanyError("Type DELETE to confirm company deletion.");
  }

  try {
    await deleteCompany(companyId);
    revalidatePath("/companies");
  } catch (error) {
    redirectWithCompanyError(getApiErrorMessage(error));
  }

  redirect("/companies?company_deleted=1");
}

export async function generateCompanyIntelligenceAction(formData: FormData) {
  const companyId = getCompanyId(formData);

  try {
    await generateCompanyIntelligence(companyId);
    revalidatePath("/companies");
  } catch (error) {
    redirectWithCompanyError(getApiErrorMessage(error));
  }

  redirect("/companies?company_intelligence=1");
}

function getCompanyId(formData: FormData) {
  const companyId = Number(getFormValue(formData, "company_id"));

  if (!Number.isInteger(companyId) || companyId <= 0) {
    redirectWithCompanyError("A valid company ID is required.");
  }

  return companyId;
}

function getFormValue(formData: FormData, key: string) {
  const value = formData.get(key);
  return typeof value === "string" ? value.trim() : "";
}

function getKeywordList(formData: FormData, key: string) {
  const value = getFormValue(formData, key);

  if (!value) {
    return [];
  }

  return value
    .split(/[\n,]/)
    .map((keyword) => keyword.trim())
    .filter(Boolean);
}

function redirectWithCompanyError(message: string): never {
  redirect(`/companies?company_error=${encodeURIComponent(message)}`);
}
