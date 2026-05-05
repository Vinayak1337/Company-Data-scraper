import type { Company } from "@/lib/api";

type KeywordField =
  | "title_keywords"
  | "negative_title_keywords"
  | "location_keywords";

export function getCompanyPriority(company: Company) {
  switch (company.priority_tier || company.priority) {
    case "dream":
      return { label: "Dream", tone: "success" as const };
    case "high":
      return { label: "High", tone: "info" as const };
    case "fallback":
      return { label: "Fallback", tone: "neutral" as const };
    case "normal":
      return { label: "Normal", tone: "neutral" as const };
    default:
      return {
        label: formatSourceType(company.priority_tier || "normal"),
        tone: "neutral" as const,
      };
  }
}

export function getScrapeStatusBadge(company: Company) {
  switch (company.source_health) {
    case "active":
      return { label: "Active", tone: "success" as const };
    case "needs_setup":
      return { label: "Needs setup", tone: "warning" as const };
    case "degraded":
      return { label: "Degraded", tone: "warning" as const };
    case "failing":
      return { label: "Failing", tone: "danger" as const };
    case "blocked":
      return { label: "Blocked", tone: "danger" as const };
    case "paused":
      return { label: "Paused", tone: "neutral" as const };
    default:
      return { label: company.source_health || "Unknown", tone: "neutral" as const };
  }
}

export function formatSourceType(sourceType: string) {
  if (!sourceType) {
    return "Unknown";
  }

  return sourceType
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function formatDateTime(value: string | null | undefined) {
  if (!value) {
    return "Never";
  }

  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function formatRelativeScan(value: string | null | undefined) {
  if (!value) {
    return "No scan yet";
  }

  const scannedAt = new Date(value).getTime();
  const elapsedMs = Date.now() - scannedAt;
  const elapsedMinutes = Math.max(1, Math.round(elapsedMs / 60000));

  if (elapsedMinutes < 60) {
    return `${elapsedMinutes}m ago`;
  }

  const elapsedHours = Math.round(elapsedMinutes / 60);
  if (elapsedHours < 48) {
    return `${elapsedHours}h ago`;
  }

  return `${Math.round(elapsedHours / 24)}d ago`;
}

export function getCompanyKeywordInputValue(
  company: Company,
  field: KeywordField,
) {
  return formatKeywordValue(company[field] ?? company.filters?.[field]);
}

export function getCompanyWorkModeFilter(company: Company) {
  return company.work_mode_filter ?? company.filters?.work_mode_filter ?? "";
}

export function formatWorkMode(value: string | null | undefined) {
  if (!value) {
    return "Any";
  }

  return formatSourceType(value);
}

function formatKeywordValue(value: string[] | string | null | undefined) {
  if (Array.isArray(value)) {
    return value.join(", ");
  }

  return typeof value === "string" ? value : "";
}
