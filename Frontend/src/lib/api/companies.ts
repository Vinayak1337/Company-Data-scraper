import { apiFetch } from "./client";
import type {
  ApiListResponse,
  AgentProvider,
  AgentProviderSetting,
  AgentRun,
  AgentRuntimeStatus,
  AlertFeedback,
  AlertFeedbackInput,
  AnalyticsOverview,
  ApplicationArtifact,
  ApplicationInput,
  ApplicationRecord,
  BackendHealth,
  CandidateProfile,
  CandidateProfileInput,
  Company,
  CompanyIntelligence,
  CompanyImportPayload,
  CompanyImportResult,
  CompanyLog,
  CompanyLogsQuery,
  CreateCompanyInput,
  DeleteCompanyResponse,
  DiagnosticsResponse,
  DeletePersonalDataResult,
  JobRecord,
  JobAlert,
  InterviewPrep,
  ManualUrlInboxInput,
  ManualUrlInboxItem,
  MatchScoreCorrectionResult,
  NotificationPreferences,
  NotificationPreferencesInput,
  OfferSupport,
  ProfileApplyTitlesResult,
  ProfileClaim,
  RunScansInput,
  RunScansResponse,
  ScrapeCompanyResponse,
  ScanJob,
  SearchStrategy,
  SearchStrategyApplyResult,
  StartAgentRunInput,
  TargetTitle,
  TodayAction,
  UpdateCompanyInput,
  UpdateAgentProviderInput,
  WorkspaceExport,
  WorkspaceImportResult,
  WeeklyReview,
} from "./types";

export function getBackendHealth() {
  return apiFetch<BackendHealth>("/health");
}

export function getDiagnostics() {
  return apiFetch<DiagnosticsResponse>("/diagnostics");
}

export function getNotificationPreferences() {
  return apiFetch<NotificationPreferences>("/notifications/preferences");
}

export function updateNotificationPreferences(input: NotificationPreferencesInput) {
  return apiFetch<NotificationPreferences>("/notifications/preferences", {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export function listCompanies() {
  return apiFetch<ApiListResponse<Company>>("/companies");
}

export function listJobs(query: { q?: string; company?: number; remote?: string; strong_fit_first?: boolean; country?: string } = {}) {
  const params = new URLSearchParams();

  if (query.q) {
    params.set("q", query.q);
  }

  if (query.company) {
    params.set("company", String(query.company));
  }

  if (query.remote) {
    params.set("remote", query.remote);
  }

  if (query.country !== undefined) {
    params.set("country", query.country);
  }

  if (query.strong_fit_first !== undefined) {
    params.set("strong_fit_first", String(query.strong_fit_first));
  }

  const suffix = params.size ? `?${params.toString()}` : "";
  return apiFetch<ApiListResponse<JobRecord>>(`/jobs${suffix}`);
}

export function getJob(jobId: number) {
  return apiFetch<JobRecord>(`/jobs/${jobId}`);
}

export function generateCompanyIntelligence(companyId: number) {
  return apiFetch<CompanyIntelligence>(`/companies/${companyId}/intelligence`, {
    method: "POST",
  });
}

export function listManualUrlInbox(status = "pending") {
  const suffix = status ? `?status=${encodeURIComponent(status)}` : "";
  return apiFetch<ApiListResponse<ManualUrlInboxItem>>(`/discovery/inbox${suffix}`);
}

export function createManualUrlInboxItem(input: ManualUrlInboxInput) {
  return apiFetch<ManualUrlInboxItem>("/discovery/inbox", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function importManualUrlInboxItem(itemId: number) {
  return apiFetch<ManualUrlInboxItem>(`/discovery/inbox/${itemId}/import`, {
    method: "POST",
  });
}

export function dismissManualUrlInboxItem(itemId: number) {
  return apiFetch<ManualUrlInboxItem>(`/discovery/inbox/${itemId}/dismiss`, {
    method: "POST",
  });
}

export function createCompany(input: CreateCompanyInput) {
  return apiFetch<Company>("/companies", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function updateCompany(companyId: number, input: UpdateCompanyInput) {
  return apiFetch<Company>(`/companies/${companyId}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export function deleteCompany(companyId: number) {
  return apiFetch<DeleteCompanyResponse>(`/companies/${companyId}`, {
    method: "DELETE",
  });
}

export function pauseCompany(companyId: number) {
  return apiFetch<Company>(`/companies/${companyId}/pause`, {
    method: "POST",
  });
}

export function resumeCompany(companyId: number) {
  return apiFetch<Company>(`/companies/${companyId}/resume`, {
    method: "POST",
  });
}

export function scrapeCompany(companyId: number) {
  return apiFetch<ScrapeCompanyResponse>(`/companies/${companyId}/rescan`, {
    method: "POST",
  });
}

export function listCompanyLogs(query: CompanyLogsQuery = {}) {
  const params = new URLSearchParams();

  if (query.company_id) {
    params.set("company_id", String(query.company_id));
  }

  if (query.limit) {
    params.set("limit", String(query.limit));
  }

  const suffix = params.size ? `?${params.toString()}` : "";
  return apiFetch<ApiListResponse<CompanyLog>>(`/companies/logs${suffix}`);
}

export function listScanJobs(query: { company_id?: number; status?: string; limit?: number } = {}) {
  const params = new URLSearchParams();

  if (query.company_id) {
    params.set("company_id", String(query.company_id));
  }

  if (query.status) {
    params.set("status", query.status);
  }

  if (query.limit) {
    params.set("limit", String(query.limit));
  }

  const suffix = params.size ? `?${params.toString()}` : "";
  return apiFetch<ApiListResponse<ScanJob>>(`/scans${suffix}`);
}

export function runScans(input: RunScansInput = {}) {
  return apiFetch<RunScansResponse>("/scans/run", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function listJobAlerts(query: { company_id?: number; status?: string; limit?: number } = {}) {
  const params = new URLSearchParams();

  if (query.company_id) {
    params.set("company_id", String(query.company_id));
  }

  if (query.status) {
    params.set("status", query.status);
  }

  if (query.limit) {
    params.set("limit", String(query.limit));
  }

  const suffix = params.size ? `?${params.toString()}` : "";
  return apiFetch<ApiListResponse<JobAlert>>(`/alerts${suffix}`);
}

export function markJobAlertRead(alertId: number) {
  return apiFetch<JobAlert>(`/alerts/${alertId}/read`, {
    method: "POST",
  });
}

export function dismissJobAlert(alertId: number) {
  return apiFetch<JobAlert>(`/alerts/${alertId}/dismiss`, {
    method: "POST",
  });
}

export function saveJobAlert(alertId: number, input: ApplicationInput = {}) {
  return apiFetch<ApplicationRecord>(`/alerts/${alertId}/save`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function skipJobAlert(alertId: number, input: ApplicationInput = {}) {
  return apiFetch<ApplicationRecord>(`/alerts/${alertId}/skip`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function listApplications(query: { status?: string; limit?: number } = {}) {
  const params = new URLSearchParams();

  if (query.status) {
    params.set("status", query.status);
  }

  if (query.limit) {
    params.set("limit", String(query.limit));
  }

  const suffix = params.size ? `?${params.toString()}` : "";
  return apiFetch<ApiListResponse<ApplicationRecord>>(`/applications${suffix}`);
}

export function createApplication(input: ApplicationInput) {
  return apiFetch<ApplicationRecord>("/applications", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function updateApplication(applicationId: number, input: ApplicationInput) {
  return apiFetch<ApplicationRecord>(`/applications/${applicationId}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export function deleteApplication(applicationId: number) {
  return apiFetch<{ deleted: boolean; id: number }>(`/applications/${applicationId}`, {
    method: "DELETE",
  });
}

export function generateApplicationTailoringArtifacts(applicationId: number) {
  return apiFetch<ApiListResponse<ApplicationArtifact>>(`/applications/${applicationId}/artifacts/generate-tailoring`, {
    method: "POST",
  });
}

export function generateApplicationInterviewPrep(applicationId: number) {
  return apiFetch<InterviewPrep>(`/applications/${applicationId}/interview-prep/generate`, {
    method: "POST",
  });
}

export function generateApplicationOfferSupport(applicationId: number) {
  return apiFetch<OfferSupport>(`/applications/${applicationId}/offer-support/generate`, {
    method: "POST",
  });
}

export function setApplicationArtifactStatus(artifactId: number, status: "draft" | "approved" | "rejected") {
  return apiFetch<ApplicationArtifact>(`/application-artifacts/${artifactId}/${status}`, {
    method: "POST",
  });
}

export function listTodayActions(query: { status?: string; limit?: number } = {}) {
  const params = new URLSearchParams();

  if (query.status) {
    params.set("status", query.status);
  }

  if (query.limit) {
    params.set("limit", String(query.limit));
  }

  const suffix = params.size ? `?${params.toString()}` : "";
  return apiFetch<ApiListResponse<TodayAction>>(`/today/actions${suffix}`);
}

export function completeTodayAction(actionId: number) {
  return apiFetch<TodayAction>(`/today/actions/${actionId}/complete`, {
    method: "POST",
  });
}

export function dismissTodayAction(actionId: number) {
  return apiFetch<TodayAction>(`/today/actions/${actionId}/dismiss`, {
    method: "POST",
  });
}

export function getProfile() {
  return apiFetch<CandidateProfile>("/profile");
}

export function updateCandidateProfile(input: CandidateProfileInput) {
  return apiFetch<CandidateProfile>("/profile", {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export function importResumeToProfile(resumeText: string) {
  return apiFetch<CandidateProfile>("/profile/import-resume", {
    method: "POST",
    body: JSON.stringify({ resume_text: resumeText }),
  });
}

export function generateProfileTargetTitles() {
  return apiFetch<CandidateProfile>("/profile/generate-titles", {
    method: "POST",
  });
}

export function setTargetTitleStatus(titleId: number, status: "suggested" | "accepted" | "rejected") {
  return apiFetch<TargetTitle>(`/profile/target-titles/${titleId}/${status}`, {
    method: "POST",
  });
}

export function setProfileClaimStatus(
  claimId: number,
  status: "unconfirmed" | "confirmed" | "needs_edit" | "rejected",
) {
  return apiFetch<ProfileClaim>(`/profile/claims/${claimId}/${status}`, {
    method: "POST",
  });
}

export function applyAcceptedTitlesToCompanies() {
  return apiFetch<ProfileApplyTitlesResult>("/profile/apply-titles-to-companies", {
    method: "POST",
  });
}

export function generateProfileSearchStrategy() {
  return apiFetch<SearchStrategy>("/profile/search-strategy/generate", {
    method: "POST",
  });
}

export function applyProfileSearchStrategyToCompanies() {
  return apiFetch<SearchStrategyApplyResult>("/profile/search-strategy/apply-to-companies", {
    method: "POST",
  });
}

export function listAgentProviders() {
  return apiFetch<ApiListResponse<AgentProviderSetting>>("/agents/providers");
}

export function getAgentRuntimeStatus() {
  return apiFetch<AgentRuntimeStatus>("/agents/runtime");
}

export function updateAgentProvider(provider: AgentProvider, input: UpdateAgentProviderInput) {
  return apiFetch<AgentProviderSetting>(`/agents/providers/${provider}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export function listAgentRuns(query: { status?: string; agent_type?: string; provider?: string; limit?: number } = {}) {
  const params = new URLSearchParams();

  if (query.status) {
    params.set("status", query.status);
  }

  if (query.agent_type) {
    params.set("agent_type", query.agent_type);
  }

  if (query.provider) {
    params.set("provider", query.provider);
  }

  if (query.limit) {
    params.set("limit", String(query.limit));
  }

  const suffix = params.size ? `?${params.toString()}` : "";
  return apiFetch<ApiListResponse<AgentRun>>(`/agents/runs${suffix}`);
}

export function startAgentRun(input: StartAgentRunInput) {
  return apiFetch<AgentRun>("/agents/runs", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function getAgentRun(runId: number) {
  return apiFetch<AgentRun>(`/agents/runs/${runId}`);
}

export function cancelAgentRun(runId: number) {
  return apiFetch<AgentRun>(`/agents/runs/${runId}/cancel`, {
    method: "POST",
  });
}

export function retryAgentRun(runId: number) {
  return apiFetch<AgentRun>(`/agents/runs/${runId}/retry`, {
    method: "POST",
  });
}

export function setAgentDecisionStatus(decisionId: number, status: "approved" | "rejected") {
  return apiFetch<AgentRun["decisions"][number]>(`/agents/decisions/${decisionId}/${status}`, {
    method: "POST",
  });
}

export function getAnalyticsOverview(limit = 12) {
  return apiFetch<AnalyticsOverview>(`/analytics?limit=${limit}`);
}

export function generateWeeklyReview() {
  return apiFetch<WeeklyReview>("/analytics/weekly-review/generate", {
    method: "POST",
  });
}

export function listAlertFeedback(query: { rating?: string; limit?: number } = {}) {
  const params = new URLSearchParams();

  if (query.rating) {
    params.set("rating", query.rating);
  }

  if (query.limit) {
    params.set("limit", String(query.limit));
  }

  const suffix = params.size ? `?${params.toString()}` : "";
  return apiFetch<ApiListResponse<AlertFeedback>>(`/analytics/feedback${suffix}`);
}

export function createAlertFeedback(input: AlertFeedbackInput) {
  return apiFetch<AlertFeedback>("/analytics/feedback", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function createMatchScoreCorrection(input: { job_id: number; correction: "too_high" | "accurate" | "too_low"; reason?: string }) {
  return apiFetch<MatchScoreCorrectionResult>("/analytics/match-corrections", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function undoLearningChange(changeId: number) {
  return apiFetch<AnalyticsOverview["learning_changes"][number]>(`/analytics/learning-changes/${changeId}/undo`, {
    method: "POST",
  });
}

export function exportWorkspaceData() {
  return apiFetch<WorkspaceExport>("/export");
}

export function importWorkspaceData(input: WorkspaceExport | Record<string, unknown>) {
  return apiFetch<WorkspaceImportResult>("/import/workspace", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function deleteAllPersonalData(confirmation: string) {
  return apiFetch<DeletePersonalDataResult>("/data/delete-all", {
    method: "POST",
    body: JSON.stringify({ confirmation }),
  });
}

export function importCompanyWatchlist(input: CompanyImportPayload) {
  return apiFetch<CompanyImportResult>("/companies/import", {
    method: "POST",
    body: JSON.stringify(input),
  });
}
