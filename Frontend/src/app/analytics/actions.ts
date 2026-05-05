"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { createAlertFeedback, generateWeeklyReview, getApiErrorMessage } from "@/lib/api";
import type { AlertFeedbackRating } from "@/lib/api";

export async function markAlertUsefulnessAction(formData: FormData) {
  const alertId = Number(getFormValue(formData, "alert_id"));
  const rating = getFormValue(formData, "rating") as AlertFeedbackRating;

  if (!Number.isInteger(alertId) || alertId <= 0) {
    redirectWithAnalyticsError("A valid alert ID is required.");
  }

  if (!["relevant", "maybe", "irrelevant"].includes(rating)) {
    redirectWithAnalyticsError("Choose relevant, maybe, or irrelevant.");
  }

  try {
    await createAlertFeedback({
      alert_id: alertId,
      rating,
      reason: getFormValue(formData, "reason"),
      tags: getFormValue(formData, "tags"),
    });
    revalidatePath("/analytics");
  } catch (error) {
    redirectWithAnalyticsError(getApiErrorMessage(error));
  }

  redirect("/analytics?analytics_notice=Feedback%20saved.");
}

export async function generateWeeklyReviewAction() {
  try {
    await generateWeeklyReview();
    revalidatePath("/analytics");
  } catch (error) {
    redirectWithAnalyticsError(getApiErrorMessage(error));
  }

  redirect("/analytics?analytics_notice=Weekly%20review%20generated.");
}

function getFormValue(formData: FormData, key: string) {
  const value = formData.get(key);
  return typeof value === "string" ? value.trim() : "";
}

function redirectWithAnalyticsError(message: string): never {
  redirect(`/analytics?analytics_error=${encodeURIComponent(message)}`);
}
