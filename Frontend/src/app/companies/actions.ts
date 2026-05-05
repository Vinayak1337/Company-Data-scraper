"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import {
  addCompanySource,
  crawlCompany,
  createCompany,
  deleteCompany,
  discoverCompanySource,
  getApiErrorMessage,
  importCompanyCsv,
  pauseCompany,
  resumeCompany,
  updateCompany,
} from "@/lib/api";

export async function addCompanyAction(formData: FormData) {
  const name = getFormValue(formData, "name");
  const domain = getFormValue(formData, "domain");
  const careersUrl = getFormValue(formData, "careers_url");
  const priorityTier = getFormValue(formData, "priority_tier") || "normal";

  if (!name && !domain && !careersUrl) {
    redirectWithCompanyError("Add a company name, domain, or careers URL.");
  }

  try {
    await createCompany({
      name: name || undefined,
      domain: domain || undefined,
      careers_url: careersUrl || undefined,
      priority_tier: priorityTier,
    });
    revalidatePath("/companies");
    revalidatePath("/");
  } catch (error) {
    redirectWithCompanyError(getApiErrorMessage(error));
  }

  redirect("/companies?company_added=1");
}

export async function importCompaniesCsvAction(formData: FormData) {
  const csv = getFormValue(formData, "company_csv");
  if (!csv) {
    redirectWithCompanyError("Paste CSV content before importing.");
  }

  let result;
  try {
    result = await importCompanyCsv(csv);
    revalidatePath("/companies");
    revalidatePath("/");
  } catch (error) {
    redirectWithCompanyError(getApiErrorMessage(error));
  }

  redirect(
    `/companies?company_notice=${encodeURIComponent(
      `CSV import finished: ${result.created_or_updated} companies, ${result.errors.length} row errors.`,
    )}`,
  );
}

export async function crawlCompanyAction(formData: FormData) {
  const companyId = getCompanyId(formData);
  let result;

  try {
    result = await crawlCompany(companyId);
    revalidatePath("/companies");
    revalidatePath("/jobs");
    revalidatePath("/");
  } catch (error) {
    redirectWithCompanyError(getApiErrorMessage(error));
  }

  const message = [
    `crawl_status=${encodeURIComponent(result.status)}`,
    `jobs_found=${encodeURIComponent(String(result.jobs_found))}`,
    `jobs_created=${encodeURIComponent(String(result.jobs_created))}`,
    `jobs_updated=${encodeURIComponent(String(result.jobs_updated))}`,
  ].join("&");

  redirect(`/companies?${message}`);
}

export async function discoverCompanySourceAction(formData: FormData) {
  const companyId = getCompanyId(formData);

  try {
    await discoverCompanySource(companyId);
    revalidatePath("/companies");
    revalidatePath("/");
  } catch (error) {
    redirectWithCompanyError(getApiErrorMessage(error));
  }

  redirect("/companies?company_notice=Source%20discovery%20updated.");
}

export async function addCompanySourceAction(formData: FormData) {
  const companyId = getCompanyId(formData);
  const url = getFormValue(formData, "source_url");
  if (!url) {
    redirectWithCompanyError("Source URL is required.");
  }

  try {
    await addCompanySource(companyId, { url, is_primary: true });
    revalidatePath("/companies");
  } catch (error) {
    redirectWithCompanyError(getApiErrorMessage(error));
  }

  redirect("/companies?company_notice=Primary%20source%20updated.");
}

export async function updateCompanyAction(formData: FormData) {
  const companyId = getCompanyId(formData);
  const scanFrequencyHours = Number(getFormValue(formData, "scan_frequency_hours") || "24");

  try {
    await updateCompany(companyId, {
      name: getFormValue(formData, "name"),
      domain: getFormValue(formData, "domain"),
      homepage_url: getFormValue(formData, "homepage_url"),
      priority_tier: getFormValue(formData, "priority_tier") || "normal",
      title_keywords: getKeywordList(formData, "title_keywords"),
      negative_title_keywords: getKeywordList(formData, "negative_title_keywords"),
      location_keywords: getKeywordList(formData, "location_keywords"),
      work_mode_filter: getFormValue(formData, "work_mode_filter"),
      scan_frequency_hours:
        Number.isInteger(scanFrequencyHours) && scanFrequencyHours > 0
          ? scanFrequencyHours
          : 24,
      alert_new_roles: formData.get("alert_new_roles") === "on",
      notes: getFormValue(formData, "notes"),
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
      redirectPath = "/companies?company_paused=1";
    }

    if (operation === "resume") {
      await resumeCompany(companyId);
      redirectPath = "/companies?company_resumed=1";
    }
    revalidatePath("/companies");
    revalidatePath("/");
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
    revalidatePath("/");
  } catch (error) {
    redirectWithCompanyError(getApiErrorMessage(error));
  }

  redirect("/companies?company_deleted=1");
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
