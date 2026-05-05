import { apiFetch } from "./client";
import type {
  AgentProvider,
  AgentRun,
  AgentRuntimeStatus,
  ApiListResponse,
  BackendHealth,
  CandidateProfile,
  CandidateProfileInput,
  Company,
  CompanyImportResult,
  CompanyJobSource,
  CompanyLog,
  CrawlResponse,
  CrawlRun,
  CreateCompanyInput,
  DiagnosticsResponse,
  JobRecord,
  MatchFeedbackInput,
  MatchFeedbackResult,
  NotificationPreferences,
  NotificationPreferencesInput,
  RunCrawlsResponse,
  SearchStrategy,
  StartAgentRunInput,
  ProfileClaim,
  TargetTitle,
  UpdateCompanyInput,
} from "./types";

export function getBackendHealth() {
  return apiFetch<BackendHealth>("/health");
}

export function getDiagnostics() {
  return apiFetch<DiagnosticsResponse>("/diagnostics");
}

export function getProfile() {
  return apiFetch<CandidateProfile>("/profile");
}

export function updateProfile(input: CandidateProfileInput) {
  return apiFetch<CandidateProfile>("/profile", {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export const updateCandidateProfile = updateProfile;

export function importResume(resumeText: string) {
  return apiFetch<CandidateProfile>("/profile/import-resume", {
    method: "POST",
    body: JSON.stringify({ resume_text: resumeText }),
  });
}

export const importResumeToProfile = importResume;

export function generateTargetTitles() {
  return apiFetch<CandidateProfile>("/profile/generate-titles", {
    method: "POST",
  });
}

export const generateProfileTargetTitles = generateTargetTitles;

export function setTargetTitleStatus(titleId: number, status: string) {
  return apiFetch<TargetTitle>(`/profile/target-titles/${titleId}/${status}`, {
    method: "POST",
  });
}

export function setProfileClaimStatus(claimId: number, status: string) {
  return apiFetch<ProfileClaim>(`/profile/claims/${claimId}/${status}`, {
    method: "POST",
  });
}

export function generateSearchStrategy() {
  return apiFetch<SearchStrategy>("/profile/search-strategy/generate", {
    method: "POST",
  });
}

export const generateProfileSearchStrategy = generateSearchStrategy;

export function applySearchStrategy() {
  return apiFetch<{ updated_count: number }>("/profile/search-strategy/apply-to-companies", {
    method: "POST",
  });
}

export const applyProfileSearchStrategyToCompanies = applySearchStrategy;

export function applyAcceptedTitles() {
  return apiFetch<{ updated_count: number }>("/profile/apply-titles-to-companies", {
    method: "POST",
  });
}

export const applyAcceptedTitlesToCompanies = applyAcceptedTitles;

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

export function createCompany(input: CreateCompanyInput) {
  return apiFetch<Company>("/companies", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function importCompanyCsv(csv: string) {
  return apiFetch<CompanyImportResult>("/companies/import-csv", {
    method: "POST",
    body: JSON.stringify({ csv }),
  });
}

export function updateCompany(companyId: number, input: UpdateCompanyInput) {
  return apiFetch<Company>(`/companies/${companyId}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export function deleteCompany(companyId: number) {
  return apiFetch<{ deleted: boolean; id: number }>(`/companies/${companyId}`, {
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

export function discoverCompanySource(companyId: number) {
  return apiFetch<{ company: Company; sources: CompanyJobSource[] }>(`/companies/${companyId}/discover-source`, {
    method: "POST",
  });
}

export function addCompanySource(companyId: number, input: { url: string; is_primary?: boolean }) {
  return apiFetch<CompanyJobSource>(`/companies/${companyId}/sources`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function crawlCompany(companyId: number) {
  return apiFetch<CrawlResponse>(`/companies/${companyId}/crawl`, {
    method: "POST",
  });
}

export function listCompanyLogs(query: { company_id?: number; limit?: number } = {}) {
  const params = new URLSearchParams();
  if (query.company_id) params.set("company_id", String(query.company_id));
  if (query.limit) params.set("limit", String(query.limit));
  const suffix = params.size ? `?${params.toString()}` : "";
  return apiFetch<ApiListResponse<CompanyLog>>(`/companies/logs${suffix}`);
}

export function listCrawlRuns(query: { company_id?: number; limit?: number } = {}) {
  const params = new URLSearchParams();
  if (query.company_id) params.set("company_id", String(query.company_id));
  if (query.limit) params.set("limit", String(query.limit));
  const suffix = params.size ? `?${params.toString()}` : "";
  return apiFetch<ApiListResponse<CrawlRun>>(`/crawls${suffix}`);
}

export function runDueCrawls(input: { limit?: number; force?: boolean; dry_run?: boolean } = {}) {
  return apiFetch<RunCrawlsResponse>("/crawls/run-due", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function listJobs(query: { q?: string; company?: number; status?: string; strong_fit_first?: boolean; limit?: number } = {}) {
  const params = new URLSearchParams();
  if (query.q) params.set("q", query.q);
  if (query.company) params.set("company", String(query.company));
  if (query.status) params.set("status", query.status);
  if (query.strong_fit_first !== undefined) params.set("strong_fit_first", String(query.strong_fit_first));
  if (query.limit) params.set("limit", String(query.limit));
  const suffix = params.size ? `?${params.toString()}` : "";
  return apiFetch<ApiListResponse<JobRecord>>(`/jobs${suffix}`);
}

export function getJob(jobId: number) {
  return apiFetch<JobRecord>(`/jobs/${jobId}`);
}

export function submitJobFeedback(jobId: number, input: MatchFeedbackInput) {
  return apiFetch<MatchFeedbackResult>(`/jobs/${jobId}/feedback`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function listAgentProviders() {
  return apiFetch<ApiListResponse<AgentProvider>>("/agents/providers");
}

export function updateAgentProvider(provider: string, input: Partial<AgentProvider>) {
  return apiFetch<AgentProvider>(`/agents/providers/${provider}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export function getAgentRuntime() {
  return apiFetch<AgentRuntimeStatus>("/agents/runtime");
}

export function listAgentRuns(limit = 20) {
  return apiFetch<ApiListResponse<AgentRun>>(`/agents/runs?limit=${limit}`);
}

export function startAgentRun(input: StartAgentRunInput) {
  return apiFetch<AgentRun>("/agents/runs", {
    method: "POST",
    body: JSON.stringify(input),
  });
}
