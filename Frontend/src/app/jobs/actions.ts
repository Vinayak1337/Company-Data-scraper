"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { getApiErrorMessage, submitJobFeedback } from "@/lib/api";

export async function submitJobFeedbackAction(formData: FormData) {
  const jobId = Number(getFormValue(formData, "job_id"));
  const feedbackType = getFormValue(formData, "feedback_type");

  if (!Number.isInteger(jobId) || jobId <= 0) {
    redirectWithJobsError("A valid job is required.");
  }

  if (!feedbackType) {
    redirectWithJobsError("Choose feedback before submitting.");
  }

  try {
    await submitJobFeedback(jobId, {
      feedback_type: feedbackType,
      notes: getFormValue(formData, "notes"),
    });
    revalidatePath("/jobs");
    revalidatePath("/");
  } catch (error) {
    redirectWithJobsError(getApiErrorMessage(error));
  }

  redirect("/jobs?jobs_notice=Feedback%20saved.");
}

function getFormValue(formData: FormData, key: string) {
  const value = formData.get(key);
  return typeof value === "string" ? value.trim() : "";
}

function redirectWithJobsError(message: string): never {
  redirect(`/jobs?jobs_error=${encodeURIComponent(message)}`);
}
