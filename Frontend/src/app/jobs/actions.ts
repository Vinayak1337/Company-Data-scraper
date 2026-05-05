"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import {
  createApplication,
  createManualUrlInboxItem,
  dismissManualUrlInboxItem,
  getApiErrorMessage,
  importManualUrlInboxItem,
} from "@/lib/api";

export async function addManualUrlAction(formData: FormData) {
  const url = getFormValue(formData, "url");
  if (!url) {
    redirectWithJobsError("Paste a company or job URL first.");
  }

  try {
    await createManualUrlInboxItem({
      url,
      item_type: getFormValue(formData, "item_type") || "unknown",
      title: getFormValue(formData, "title"),
      notes: getFormValue(formData, "notes"),
    });
    revalidatePath("/jobs");
  } catch (error) {
    redirectWithJobsError(getApiErrorMessage(error));
  }

  redirect("/jobs?jobs_notice=URL%20added%20to%20inbox.");
}

export async function importManualUrlAction(formData: FormData) {
  const itemId = Number(getFormValue(formData, "item_id"));
  if (!Number.isInteger(itemId) || itemId <= 0) {
    redirectWithJobsError("A valid inbox item is required.");
  }

  try {
    await importManualUrlInboxItem(itemId);
    revalidatePath("/jobs");
    revalidatePath("/companies");
  } catch (error) {
    redirectWithJobsError(getApiErrorMessage(error));
  }

  redirect("/jobs?jobs_notice=URL%20imported.");
}

export async function dismissManualUrlAction(formData: FormData) {
  const itemId = Number(getFormValue(formData, "item_id"));
  if (!Number.isInteger(itemId) || itemId <= 0) {
    redirectWithJobsError("A valid inbox item is required.");
  }

  try {
    await dismissManualUrlInboxItem(itemId);
    revalidatePath("/jobs");
  } catch (error) {
    redirectWithJobsError(getApiErrorMessage(error));
  }

  redirect("/jobs?jobs_notice=URL%20dismissed.");
}

export async function saveJobAsApplicationAction(formData: FormData) {
  const jobId = Number(getFormValue(formData, "job_id"));
  if (!Number.isInteger(jobId) || jobId <= 0) {
    redirectWithJobsError("A valid job is required.");
  }

  try {
    await createApplication({
      job_id: jobId,
      status: "saved",
      next_action: getFormValue(formData, "next_action"),
    });
    revalidatePath("/jobs");
    revalidatePath("/applications");
  } catch (error) {
    redirectWithJobsError(getApiErrorMessage(error));
  }

  redirect("/jobs?jobs_notice=Job%20saved%20to%20applications.");
}

export async function skipJobAsApplicationAction(formData: FormData) {
  const jobId = Number(getFormValue(formData, "job_id"));
  if (!Number.isInteger(jobId) || jobId <= 0) {
    redirectWithJobsError("A valid job is required.");
  }

  try {
    await createApplication({
      job_id: jobId,
      status: "skipped",
      next_action: "Skipped from job review",
    });
    revalidatePath("/jobs");
    revalidatePath("/applications");
  } catch (error) {
    redirectWithJobsError(getApiErrorMessage(error));
  }

  redirect("/jobs?jobs_notice=Job%20skipped.");
}

function getFormValue(formData: FormData, key: string) {
  const value = formData.get(key);
  return typeof value === "string" ? value.trim() : "";
}

function redirectWithJobsError(message: string): never {
  redirect(`/jobs?jobs_error=${encodeURIComponent(message)}`);
}
