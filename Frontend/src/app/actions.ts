"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { getApiErrorMessage, runDueCrawls, startAgentRun } from "@/lib/api";

export async function runDueCrawlsAction(formData: FormData) {
  const limit = Number(getFormValue(formData, "limit") || "10");
  let notice = "";

  try {
    const result = await runDueCrawls({
      limit: Number.isInteger(limit) && limit > 0 ? limit : 10,
    });
    notice = `Crawls finished: ${result.scanned} scanned, ${result.failed} failed, ${result.alerts_created} notifications queued.`;
    revalidatePath("/");
    revalidatePath("/companies");
    revalidatePath("/jobs");
  } catch (error) {
    redirectWithTodayError(getApiErrorMessage(error));
  }

  redirect(`/?today_notice=${encodeURIComponent(notice)}`);
}

export async function runAgentAction(formData: FormData) {
  const agentType = getFormValue(formData, "agent_type");
  if (!agentType) {
    redirectWithTodayError("Agent type is required.");
  }

  try {
    await startAgentRun({
      agent_type: agentType,
      provider: "direct_api",
      tool_policy: "read_only",
    });
    revalidatePath("/");
  } catch (error) {
    redirectWithTodayError(getApiErrorMessage(error));
  }

  redirect("/?today_notice=Agent%20review%20completed.");
}

function getFormValue(formData: FormData, key: string) {
  const value = formData.get(key);
  return typeof value === "string" ? value.trim() : "";
}

function redirectWithTodayError(message: string): never {
  redirect(`/?today_error=${encodeURIComponent(message)}`);
}
