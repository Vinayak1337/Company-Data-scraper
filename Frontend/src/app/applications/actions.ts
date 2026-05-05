"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import {
  generateApplicationTailoringArtifacts,
  generateApplicationInterviewPrep,
  generateApplicationOfferSupport,
  getApiErrorMessage,
  setApplicationArtifactStatus,
  updateApplication,
} from "@/lib/api";

export async function updateApplicationAction(formData: FormData) {
  const applicationId = Number(getFormValue(formData, "application_id"));

  if (!Number.isInteger(applicationId) || applicationId <= 0) {
    redirectWithApplicationsError("A valid application ID is required.");
  }

  try {
    await updateApplication(applicationId, {
      status: getFormValue(formData, "status"),
      notes: getFormValue(formData, "notes"),
      next_action: getFormValue(formData, "next_action"),
      follow_up_at: normalizeDateInput(getFormValue(formData, "follow_up_at")),
    });
    revalidatePath("/");
    revalidatePath("/applications");
  } catch (error) {
    redirectWithApplicationsError(getApiErrorMessage(error));
  }

  redirect("/applications?applications_notice=Application%20updated.");
}

export async function generateApplicationArtifactsAction(formData: FormData) {
  const applicationId = Number(getFormValue(formData, "application_id"));

  if (!Number.isInteger(applicationId) || applicationId <= 0) {
    redirectWithApplicationsError("A valid application ID is required.");
  }

  try {
    await generateApplicationTailoringArtifacts(applicationId);
    revalidatePath("/applications");
  } catch (error) {
    redirectWithApplicationsError(getApiErrorMessage(error));
  }

  redirect("/applications?applications_notice=Application%20artifacts%20generated.");
}

export async function setApplicationArtifactStatusAction(formData: FormData) {
  const artifactId = Number(getFormValue(formData, "artifact_id"));
  const status = getFormValue(formData, "status");

  if (!Number.isInteger(artifactId) || artifactId <= 0) {
    redirectWithApplicationsError("A valid artifact ID is required.");
  }

  if (!["draft", "approved", "rejected"].includes(status)) {
    redirectWithApplicationsError("Choose a valid artifact status.");
  }

  try {
    await setApplicationArtifactStatus(artifactId, status as "draft" | "approved" | "rejected");
    revalidatePath("/applications");
  } catch (error) {
    redirectWithApplicationsError(getApiErrorMessage(error));
  }

  redirect("/applications?applications_notice=Artifact%20updated.");
}

export async function generateInterviewPrepAction(formData: FormData) {
  const applicationId = Number(getFormValue(formData, "application_id"));

  if (!Number.isInteger(applicationId) || applicationId <= 0) {
    redirectWithApplicationsError("A valid application ID is required.");
  }

  try {
    await generateApplicationInterviewPrep(applicationId);
    revalidatePath("/applications");
  } catch (error) {
    redirectWithApplicationsError(getApiErrorMessage(error));
  }

  redirect("/applications?applications_notice=Interview%20prep%20generated.");
}

export async function generateOfferSupportAction(formData: FormData) {
  const applicationId = Number(getFormValue(formData, "application_id"));

  if (!Number.isInteger(applicationId) || applicationId <= 0) {
    redirectWithApplicationsError("A valid application ID is required.");
  }

  try {
    await generateApplicationOfferSupport(applicationId);
    revalidatePath("/applications");
  } catch (error) {
    redirectWithApplicationsError(getApiErrorMessage(error));
  }

  redirect("/applications?applications_notice=Offer%20support%20generated.");
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

function redirectWithApplicationsError(message: string): never {
  redirect(`/applications?applications_error=${encodeURIComponent(message)}`);
}
