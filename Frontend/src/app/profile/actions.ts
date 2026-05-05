"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import {
  applyAcceptedTitlesToCompanies,
  applyProfileSearchStrategyToCompanies,
  generateProfileSearchStrategy,
  generateProfileTargetTitles,
  getApiErrorMessage,
  importResumeToProfile,
  setProfileClaimStatus,
  setTargetTitleStatus,
  updateCandidateProfile,
} from "@/lib/api";
import type { CandidateProfileInput } from "@/lib/api";

export async function updateProfileAction(formData: FormData) {
  const input: CandidateProfileInput = {};
  setStringValue(input, formData, "full_name");
  setStringValue(input, formData, "headline");
  setStringValue(input, formData, "location");
  setStringValue(input, formData, "remote_preference");
  setListValue(input, formData, "target_locations");
  setListValue(input, formData, "preferred_work_modes");
  setListValue(input, formData, "skills");
  setStringValue(input, formData, "summary");
  setStringValue(input, formData, "dealbreakers");
  setStringValue(input, formData, "compensation_expectation");
  setStringValue(input, formData, "cv_markdown");
  setStringValue(input, formData, "profile_markdown");
  setStringValue(input, formData, "profile_yml");
  setStringValue(input, formData, "role_framing");

  if (formData.has("github_url") || formData.has("linkedin_url") || formData.has("portfolio_url")) {
    input.links = {
      github: getFormValue(formData, "github_url"),
      linkedin: getFormValue(formData, "linkedin_url"),
      portfolio: getFormValue(formData, "portfolio_url"),
    };
  }

  try {
    await updateCandidateProfile(input);
    revalidatePath("/profile");
  } catch (error) {
    redirectWithProfileError(getApiErrorMessage(error));
  }

  redirect("/profile?profile_notice=Profile%20updated.");
}

export async function importResumeAction(formData: FormData) {
  const resumeText = getFormValue(formData, "resume_text");

  if (!resumeText) {
    redirectWithProfileError("Paste resume or CV text before importing.");
  }

  try {
    await importResumeToProfile(resumeText);
    revalidatePath("/profile");
  } catch (error) {
    redirectWithProfileError(getApiErrorMessage(error));
  }

  redirect("/profile?profile_notice=Resume%20imported.");
}

export async function generateTargetTitlesAction() {
  try {
    await generateProfileTargetTitles();
    revalidatePath("/profile");
  } catch (error) {
    redirectWithProfileError(getApiErrorMessage(error));
  }

  redirect("/profile?profile_notice=Target%20titles%20generated.");
}

export async function setTargetTitleStatusAction(formData: FormData) {
  const titleId = Number(getFormValue(formData, "title_id"));
  const status = getFormValue(formData, "status");

  if (!Number.isInteger(titleId) || titleId <= 0) {
    redirectWithProfileError("A valid target title ID is required.");
  }

  if (!["suggested", "accepted", "rejected"].includes(status)) {
    redirectWithProfileError("Choose a valid target title status.");
  }

  try {
    await setTargetTitleStatus(titleId, status as "suggested" | "accepted" | "rejected");
    revalidatePath("/profile");
  } catch (error) {
    redirectWithProfileError(getApiErrorMessage(error));
  }

  redirect("/profile?profile_notice=Target%20title%20updated.");
}

export async function setProfileClaimStatusAction(formData: FormData) {
  const claimId = Number(getFormValue(formData, "claim_id"));
  const status = getFormValue(formData, "status");

  if (!Number.isInteger(claimId) || claimId <= 0) {
    redirectWithProfileError("A valid claim ID is required.");
  }

  if (!["unconfirmed", "confirmed", "needs_edit", "rejected"].includes(status)) {
    redirectWithProfileError("Choose a valid claim status.");
  }

  try {
    await setProfileClaimStatus(
      claimId,
      status as "unconfirmed" | "confirmed" | "needs_edit" | "rejected",
    );
    revalidatePath("/profile");
  } catch (error) {
    redirectWithProfileError(getApiErrorMessage(error));
  }

  redirect("/profile?profile_notice=Claim%20updated.");
}

export async function applyAcceptedTitlesAction() {
  let updatedCount = 0;

  try {
    const result = await applyAcceptedTitlesToCompanies();
    updatedCount = result.updated_count;
    revalidatePath("/profile");
    revalidatePath("/companies");
  } catch (error) {
    redirectWithProfileError(getApiErrorMessage(error));
  }

  redirect(`/profile?profile_notice=${encodeURIComponent(`Updated ${updatedCount} company filters.`)}`);
}

export async function generateSearchStrategyAction() {
  try {
    await generateProfileSearchStrategy();
    revalidatePath("/profile");
  } catch (error) {
    redirectWithProfileError(getApiErrorMessage(error));
  }

  redirect("/profile?profile_notice=Search%20strategy%20generated.");
}

export async function applySearchStrategyAction() {
  let updatedCount = 0;

  try {
    const result = await applyProfileSearchStrategyToCompanies();
    updatedCount = result.updated_count;
    revalidatePath("/profile");
    revalidatePath("/companies");
  } catch (error) {
    redirectWithProfileError(getApiErrorMessage(error));
  }

  redirect(`/profile?profile_notice=${encodeURIComponent(`Updated ${updatedCount} company filters from search strategy.`)}`);
}

function getFormValue(formData: FormData, key: string) {
  const value = formData.get(key);
  return typeof value === "string" ? value.trim() : "";
}

function getListValue(formData: FormData, key: string) {
  return getFormValue(formData, key)
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function setStringValue(input: CandidateProfileInput, formData: FormData, key: keyof CandidateProfileInput & string) {
  if (formData.has(key)) {
    input[key] = getFormValue(formData, key) as never;
  }
}

function setListValue(input: CandidateProfileInput, formData: FormData, key: keyof CandidateProfileInput & string) {
  if (formData.has(key)) {
    input[key] = getListValue(formData, key) as never;
  }
}

function redirectWithProfileError(message: string): never {
  redirect(`/profile?profile_error=${encodeURIComponent(message)}`);
}
