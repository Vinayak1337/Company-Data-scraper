"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import {
  completeTodayAction,
  dismissJobAlert,
  dismissTodayAction,
  getApiErrorMessage,
  markJobAlertRead,
  runScans,
  saveJobAlert,
  skipJobAlert,
} from "@/lib/api";

export async function runDueScansAction(formData: FormData) {
  const limit = Number(getFormValue(formData, "limit") || "10");
  let notice = "";

  try {
    const result = await runScans({
      limit: Number.isInteger(limit) && limit > 0 ? limit : 10,
    });
    notice = `Scans finished: ${result.scanned} scanned, ${result.failed} failed, ${result.alerts_created} alerts created.`;
    revalidatePath("/");
    revalidatePath("/companies");
  } catch (error) {
    redirectWithTodayError(getApiErrorMessage(error));
  }

  redirect(`/?today_notice=${encodeURIComponent(notice)}`);
}

export async function markAlertReadAction(formData: FormData) {
  const alertId = getAlertId(formData);

  try {
    await markJobAlertRead(alertId);
    revalidatePath("/");
  } catch (error) {
    redirectWithTodayError(getApiErrorMessage(error));
  }

  redirect("/?today_notice=Alert%20marked%20read.");
}

export async function dismissAlertAction(formData: FormData) {
  const alertId = getAlertId(formData);

  try {
    await dismissJobAlert(alertId);
    revalidatePath("/");
  } catch (error) {
    redirectWithTodayError(getApiErrorMessage(error));
  }

  redirect("/?today_notice=Alert%20dismissed.");
}

export async function saveAlertAsApplicationAction(formData: FormData) {
  const alertId = getAlertId(formData);
  const nextAction = getFormValue(formData, "next_action");
  const followUpAt = normalizeDateInput(getFormValue(formData, "follow_up_at"));

  try {
    await saveJobAlert(alertId, {
      status: "saved",
      next_action: nextAction || "Review and decide whether to apply",
      follow_up_at: followUpAt,
    });
    revalidatePath("/");
    revalidatePath("/applications");
  } catch (error) {
    redirectWithTodayError(getApiErrorMessage(error));
  }

  redirect("/?today_notice=Role%20saved%20to%20applications.");
}

export async function skipAlertAsApplicationAction(formData: FormData) {
  const alertId = getAlertId(formData);
  const notes = getFormValue(formData, "notes");

  try {
    await skipJobAlert(alertId, {
      notes: notes || "Skipped from Today.",
    });
    revalidatePath("/");
    revalidatePath("/applications");
  } catch (error) {
    redirectWithTodayError(getApiErrorMessage(error));
  }

  redirect("/?today_notice=Role%20skipped.");
}

export async function completeTodayActionAction(formData: FormData) {
  const actionId = getTodayActionId(formData);

  try {
    await completeTodayAction(actionId);
    revalidatePath("/");
  } catch (error) {
    redirectWithTodayError(getApiErrorMessage(error));
  }

  redirect("/?today_notice=Today%20action%20completed.");
}

export async function dismissTodayActionAction(formData: FormData) {
  const actionId = getTodayActionId(formData);

  try {
    await dismissTodayAction(actionId);
    revalidatePath("/");
  } catch (error) {
    redirectWithTodayError(getApiErrorMessage(error));
  }

  redirect("/?today_notice=Today%20action%20dismissed.");
}

function getAlertId(formData: FormData) {
  const alertId = Number(getFormValue(formData, "alert_id"));

  if (!Number.isInteger(alertId) || alertId <= 0) {
    redirectWithTodayError("A valid alert ID is required.");
  }

  return alertId;
}

function getTodayActionId(formData: FormData) {
  const actionId = Number(getFormValue(formData, "action_id"));

  if (!Number.isInteger(actionId) || actionId <= 0) {
    redirectWithTodayError("A valid Today action ID is required.");
  }

  return actionId;
}

function getFormValue(formData: FormData, key: string) {
  const value = formData.get(key);
  return typeof value === "string" ? value.trim() : "";
}

function normalizeDateInput(value: string) {
  if (!value) {
    return null;
  }

  if (value.includes("T")) {
    return value;
  }

  return `${value}T09:00:00`;
}

function redirectWithTodayError(message: string): never {
  redirect(`/?today_error=${encodeURIComponent(message)}`);
}
