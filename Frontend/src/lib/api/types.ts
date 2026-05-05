export type ApiListResponse<T> = {
  count: number;
  results: T[];
};

export type BackendHealth = {
  status: "ok" | "error" | string;
};

export type ScrapeStatus = "never" | "success" | "failed" | string;
export type SourceHealth =
  | "needs_setup"
  | "active"
  | "degraded"
  | "failing"
  | "paused"
  | "blocked"
  | string;
export type PriorityTier = "dream" | "high" | "normal" | "fallback" | string;
export type WorkModeFilter = "" | "remote" | "hybrid" | "onsite" | string;

export type KeywordListValue = string[] | string | null;

export type CompanyFilters = {
  title_keywords?: KeywordListValue;
  negative_title_keywords?: KeywordListValue;
  location_keywords?: KeywordListValue;
  work_mode_filter?: WorkModeFilter | null;
};

export type Company = {
  id: number;
  name: string;
  careers_url: string;
  priority: PriorityTier;
  priority_tier: PriorityTier;
  scraper_type: string;
  is_active: boolean;
  is_paused: boolean;
  state: "active" | "paused" | string;
  source_health: SourceHealth;
  last_scraped_at: string | null;
  last_scrape_status: ScrapeStatus;
  last_scrape_message: string;
  last_successful_scan_at: string | null;
  last_failed_scan_at: string | null;
  consecutive_failure_count: number;
  last_new_role_at: string | null;
  created_at: string | null;
  updated_at: string | null;
  title_keywords?: KeywordListValue;
  negative_title_keywords?: KeywordListValue;
  location_keywords?: KeywordListValue;
  work_mode_filter?: WorkModeFilter | null;
  scan_frequency_hours: number;
  alert_new_roles: boolean;
  latest_intelligence: CompanyIntelligence | null;
  recruiter_contacts_count: number;
  filters?: CompanyFilters | null;
};

export type CompanyIntelligence = {
  id: number;
  company_id: number;
  summary: string;
  research_notes: string;
  hiring_signals: Array<Record<string, unknown>>;
  role_patterns: Array<Record<string, unknown>>;
  role_legitimacy: string;
  caveats: Array<Record<string, unknown>>;
  hiring_team_hints: Array<Record<string, unknown>>;
  interview_process_notes: string;
  risk_flags: Array<Record<string, unknown>>;
  user_notes: string;
  source_snapshot: Record<string, unknown>;
  verification_status: string;
  generated_by: string;
  created_at: string | null;
};

export type CreateCompanyInput = {
  name?: string;
  careers_url: string;
  priority_tier?: PriorityTier;
  title_keywords?: string[];
  negative_title_keywords?: string[];
  location_keywords?: string[];
  work_mode_filter?: WorkModeFilter;
  scan_frequency_hours?: number;
  alert_new_roles?: boolean;
};

export type UpdateCompanyInput = {
  name?: string;
  careers_url?: string;
  scraper_type?: string;
  priority_tier?: PriorityTier;
  priority?: PriorityTier;
  is_active?: boolean;
  is_paused?: boolean;
  state?: "active" | "paused" | string;
  title_keywords?: string[];
  negative_title_keywords?: string[];
  location_keywords?: string[];
  work_mode_filter?: WorkModeFilter;
  scan_frequency_hours?: number;
  alert_new_roles?: boolean;
};

export type DeleteCompanyResponse = {
  deleted: boolean;
  id: number;
};

export type ScrapeCompanyResponse = {
  status: "success" | "failed" | string;
  message: string;
  jobs_found: number;
  jobs_created: number;
  jobs_updated: number;
  company?: Company;
  log?: {
    id: number;
    status: string;
    source_platform: string;
    jobs_found: number;
    jobs_created: number;
    jobs_updated: number;
    message: string;
    started_at: string | null;
    finished_at: string | null;
  };
  scan_job?: ScanJob | null;
  alerts_created?: number;
};

export type ScanJobStatus =
  | "queued"
  | "running"
  | "success"
  | "partial_success"
  | "failed"
  | "cancelled"
  | "skipped"
  | string;

export type ScanJob = {
  id: number;
  company_id: number;
  company_name: string;
  scrape_log_id?: number | null;
  status: ScanJobStatus;
  trigger: "manual" | "scheduled" | "command" | string;
  source_platform: string;
  message: string;
  jobs_found: number;
  jobs_created: number;
  jobs_updated: number;
  alerts_created: number;
  requested_at: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type JobAlert = {
  id: number;
  company_id: number;
  company_name: string;
  job_id: number;
  job_title: string;
  job_apply_url: string;
  scan_job_id: number | null;
  alert_type: "new_role" | string;
  status: "unread" | "read" | "dismissed" | string;
  title: string;
  message: string;
  created_at: string | null;
  read_at: string | null;
  dismissed_at: string | null;
};

export type ApplicationStatus =
  | "saved"
  | "applying"
  | "applied"
  | "interviewing"
  | "offer"
  | "rejected"
  | "withdrawn"
  | "skipped"
  | string;

export type ApplicationRecord = {
  id: number;
  job_id: number;
  job_title: string;
  company_id: number;
  company_name: string;
  apply_url: string;
  location: string;
  remote_policy: string;
  source_alert_id: number | null;
  status: ApplicationStatus;
  notes: string;
  next_action: string;
  follow_up_at: string | null;
  applied_at: string | null;
  artifacts: ApplicationArtifact[];
  interview_prep: InterviewPrep | null;
  offer_support: OfferSupport | null;
  created_at: string | null;
  updated_at: string | null;
};

export type ApplicationArtifact = {
  id: number;
  application_id: number;
  artifact_type:
    | "tailoring_plan"
    | "cv_notes"
    | "cover_note"
    | "recruiter_message"
    | "answer_bank"
    | "interview_seed"
    | string;
  title: string;
  content: string;
  status: "draft" | "approved" | "rejected" | string;
  metadata: Record<string, unknown>;
  generated_by: string;
  created_at: string | null;
  updated_at: string | null;
};

export type InterviewPrep = {
  id: number;
  application_id: number;
  stage: string;
  checklist: Array<Record<string, unknown>>;
  focus_areas: string[];
  question_bank: Array<Record<string, unknown>>;
  story_bank: Array<Record<string, unknown>>;
  gaps: string[];
  notes: string;
  generated_by: string;
  created_at: string | null;
  updated_at: string | null;
};

export type OfferSupport = {
  id: number;
  application_id: number;
  offer_stage: string;
  base_salary_min: number | null;
  base_salary_max: number | null;
  equity_notes: string;
  benefits_notes: string;
  manual_research: Array<Record<string, unknown>>;
  decision_criteria: Array<Record<string, unknown>>;
  negotiation_points: Array<Record<string, unknown>>;
  compensation_notes: string;
  risk_flags: Array<Record<string, unknown>>;
  generated_by: string;
  created_at: string | null;
  updated_at: string | null;
};

export type ApplicationInput = {
  job_id?: number;
  source_alert_id?: number;
  status?: ApplicationStatus;
  notes?: string;
  next_action?: string;
  follow_up_at?: string | null;
};

export type TodayAction = {
  id: number;
  action_type: "review_new_role" | "follow_up" | "application_next_step" | string;
  status: "open" | "done" | "dismissed" | string;
  title: string;
  message: string;
  due_at: string | null;
  job_id: number | null;
  job_title: string;
  company_id: number | null;
  company_name: string;
  apply_url: string;
  application_id: number | null;
  source_alert_id: number | null;
  created_at: string | null;
  completed_at: string | null;
};

export type TargetTitle = {
  id: number;
  title: string;
  fit_bucket: "core" | "adjacent" | "stretch" | string;
  confidence_score: number;
  knowledge_accuracy: number;
  evidence: string[];
  source: string;
  status: "suggested" | "accepted" | "rejected" | string;
  created_at: string | null;
  updated_at: string | null;
};

export type ProfileClaim = {
  id: number;
  claim_type: "skill" | "experience" | "project" | "metric" | "education" | "other" | string;
  text: string;
  evidence: string;
  source: string;
  status: "unconfirmed" | "confirmed" | "needs_edit" | "rejected" | string;
  created_at: string | null;
  updated_at: string | null;
};

export type CandidateProfile = {
  id: number;
  full_name: string;
  headline: string;
  location: string;
  remote_preference: WorkModeFilter;
  target_locations: string[];
  preferred_work_modes: string[];
  links: Record<string, string>;
  skills: string[];
  summary: string;
  dealbreakers: string;
  compensation_expectation: string;
  cv_markdown: string;
  profile_markdown: string;
  profile_yml: string;
  proof_points: Array<Record<string, unknown>>;
  skill_inventory: Array<Record<string, unknown>>;
  career_timeline: Array<Record<string, unknown>>;
  role_framing: string;
  profile_completeness_score: number;
  last_generated_at: string | null;
  target_titles: TargetTitle[];
  claims: ProfileClaim[];
  search_strategy: SearchStrategy | null;
  created_at: string | null;
  updated_at: string | null;
};

export type CandidateProfileInput = Partial<
  Pick<
    CandidateProfile,
    | "full_name"
    | "headline"
    | "location"
    | "remote_preference"
    | "target_locations"
    | "preferred_work_modes"
    | "links"
    | "skills"
    | "summary"
    | "dealbreakers"
    | "compensation_expectation"
    | "cv_markdown"
    | "profile_markdown"
    | "profile_yml"
    | "proof_points"
    | "skill_inventory"
    | "career_timeline"
    | "role_framing"
  >
>;

export type ProfileApplyTitlesResult = {
  updated_count: number;
  titles: string[];
  companies: Company[];
};

export type SearchStrategy = {
  id: number;
  role_families: string[];
  target_title_keywords: string[];
  negative_keywords: string[];
  seniority_levels: string[];
  location_keywords: string[];
  work_mode_preferences: string[];
  generated_from: string;
  notes: string;
  last_generated_at: string | null;
  applied_at: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type SearchStrategyApplyResult = {
  updated_count: number;
  strategy: SearchStrategy;
  companies: Company[];
};

export type AgentProvider =
  | "direct_api"
  | "openrouter"
  | "deepseek"
  | "gemini_cli"
  | "claude_code_cli"
  | "opencode"
  | string;

export type AgentToolPolicy =
  | "read_only"
  | "workspace_write"
  | "safe_shell"
  | "network_tools"
  | "external_action"
  | string;

export type AgentRunStatus =
  | "queued"
  | "running"
  | "waiting_approval"
  | "success"
  | "failed"
  | "cancelled"
  | string;

export type AgentType =
  | "profile_builder"
  | "match_review"
  | "search_strategy"
  | "application_prep"
  | "follow_up"
  | string;

export type AgentProviderSetting = {
  id: number;
  provider: AgentProvider;
  label: string;
  model_name: string;
  enabled: boolean;
  worker_only: boolean;
  api_key_env_var: string;
  api_key_configured: boolean;
  default_tool_policy: AgentToolPolicy;
  consent_required: boolean;
  daily_run_limit: number;
  monthly_budget_cents: number;
  estimated_cost_per_run_cents: number;
  notes: string;
  created_at: string | null;
  updated_at: string | null;
};

export type AgentStep = {
  id: number;
  order: number;
  name: string;
  status: AgentRunStatus;
  message: string;
  started_at: string | null;
  finished_at: string | null;
  created_at: string | null;
};

export type AgentArtifact = {
  id: number;
  artifact_type: "markdown" | "json" | "text" | "proposal" | string;
  title: string;
  content: string;
  metadata: Record<string, unknown>;
  created_at: string | null;
};

export type AgentDecision = {
  id: number;
  decision_type: string;
  status: "pending" | "approved" | "rejected" | string;
  question: string;
  proposed_changes: Record<string, unknown>;
  decided_at: string | null;
  created_at: string | null;
};

export type AgentPermission = {
  id: number;
  policy_level: AgentToolPolicy;
  status: "granted" | "denied" | "blocked" | string;
  reason: string;
  created_at: string | null;
};

export type RuntimeInvocation = {
  id: number;
  provider: AgentProvider;
  adapter: string;
  model_name: string;
  status: "prepared" | "running" | "success" | "failed" | "skipped" | string;
  input_snapshot: Record<string, unknown>;
  output_snapshot: Record<string, unknown>;
  error: string;
  token_count: number;
  cost_estimate: number;
  started_at: string | null;
  finished_at: string | null;
  created_at: string | null;
};

export type AgentAuditLog = {
  id: number;
  event_type: string;
  message: string;
  metadata: Record<string, unknown>;
  created_at: string | null;
};

export type AgentRun = {
  id: number;
  agent_type: AgentType;
  status: AgentRunStatus;
  provider: AgentProvider;
  model_name: string;
  tool_policy: AgentToolPolicy;
  prompt_version: string;
  input_snapshot: Record<string, unknown>;
  output_snapshot: Record<string, unknown>;
  result_summary: string;
  error: string;
  user_safe_error: string;
  requested_at: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string | null;
  updated_at: string | null;
  steps: AgentStep[];
  artifacts: AgentArtifact[];
  decisions: AgentDecision[];
  permissions: AgentPermission[];
  runtime_invocations: RuntimeInvocation[];
  audit_logs: AgentAuditLog[];
};

export type StartAgentRunInput = {
  agent_type: AgentType;
  provider?: AgentProvider;
  model_name?: string;
  tool_policy?: AgentToolPolicy;
  user_consent?: boolean;
};

export type UpdateAgentProviderInput = {
  enabled?: boolean;
  model_name?: string;
  default_tool_policy?: AgentToolPolicy;
  consent_required?: boolean;
  daily_run_limit?: number;
  monthly_budget_cents?: number;
  estimated_cost_per_run_cents?: number;
  notes?: string;
};

export type AgentRuntimeProviderStatus = {
  provider: AgentProvider;
  label: string;
  enabled: boolean;
  worker_only: boolean;
  consent_required: boolean;
  daily_run_limit: number;
  daily_runs_used: number;
  daily_runs_remaining: number;
  monthly_budget_cents: number;
  monthly_spend_estimate: number;
  monthly_budget_estimate: number;
  estimated_cost_per_run_cents: number;
};

export type AgentRuntimeStatus = {
  execution_mode: "inline" | "queued" | string;
  queue_batch_size: number;
  queued_runs: number;
  running_runs: number;
  providers: AgentRuntimeProviderStatus[];
};

export type AlertFeedbackRating = "relevant" | "maybe" | "irrelevant" | string;

export type AlertFeedback = {
  id: number;
  alert_id: number;
  job_id: number;
  job_title: string;
  company_id: number;
  company_name: string;
  rating: AlertFeedbackRating;
  reason: string;
  tags: string[];
  created_at: string | null;
  updated_at: string | null;
};

export type FeedbackCandidate = {
  alert_id: number;
  job_id: number;
  company_id: number;
  company_name: string;
  job_title: string;
  location: string;
  remote_policy: string;
  status: string;
  created_at: string | null;
  apply_url: string;
};

export type CompanyQualityMetric = {
  company_id: number;
  company_name: string;
  careers_url: string;
  priority_tier: PriorityTier;
  source_platform: string;
  source_health: SourceHealth;
  is_active: boolean;
  last_successful_scan_at: string | null;
  last_failed_scan_at: string | null;
  last_new_role_at: string | null;
  scan_frequency_hours: number;
  scan_count: number;
  successful_scans: number;
  failed_scans: number;
  success_rate: number | null;
  jobs_total: number;
  alerts_total: number;
  applications_total: number;
  feedback_total: number;
  feedback_relevant: number;
  feedback_maybe: number;
  feedback_irrelevant: number;
  usefulness_score: number | null;
  stale: boolean;
  noisy: boolean;
  title_keywords: string[];
  negative_title_keywords: string[];
  location_keywords: string[];
  work_mode_filter: WorkModeFilter;
};

export type PlatformQualityMetric = {
  source_platform: string;
  companies_total: number;
  active_companies: number;
  scan_count: number;
  success_rate: number | null;
  alerts_total: number;
  feedback_total: number;
  usefulness_score: number | null;
  failing_sources: number;
  noisy_companies: number;
};

export type AnalyticsSignal = {
  kind: string;
  company_id: number;
  company_name: string;
  message: string;
  evidence: Record<string, unknown>;
};

export type FilterSuggestion = {
  company_id: number;
  company_name: string;
  suggestion_type: string;
  message: string;
  evidence: string[];
  action: string;
  payload: Record<string, unknown>;
  requires_review: boolean;
};

export type AnalyticsOverview = {
  generated_at: string;
  summary: {
    companies_tracked: number;
    sources_active: number;
    sources_failing: number;
    alerts_total: number;
    feedback_total: number;
    feedback_relevant: number;
    feedback_maybe: number;
    feedback_irrelevant: number;
    suggestions_total: number;
  };
  company_metrics: CompanyQualityMetric[];
  platform_metrics: PlatformQualityMetric[];
  feedback_inbox: FeedbackCandidate[];
  noisy_signals: AnalyticsSignal[];
  filter_suggestions: FilterSuggestion[];
  recent_feedback: AlertFeedback[];
  latest_weekly_review: WeeklyReview | null;
  learning_changes: LearningChange[];
};

export type WeeklyReview = {
  id: number;
  period_start: string | null;
  period_end: string | null;
  summary: string;
  recommendations: Array<Record<string, unknown>>;
  risks: Array<Record<string, unknown>>;
  metrics_snapshot: Record<string, unknown>;
  generated_by: string;
  created_at: string | null;
};

export type LearningChange = {
  id: number;
  change_type: string;
  status: "active" | "undone" | string;
  summary: string;
  evidence: Array<Record<string, unknown>>;
  payload: Record<string, unknown>;
  created_at: string | null;
  undone_at: string | null;
};

export type MatchScoreCorrection = {
  id: number;
  job_id: number;
  job_title: string;
  company_id: number;
  company_name: string;
  profile_id: number | null;
  learning_change_id: number;
  learning_change_status: "active" | "undone" | string;
  correction: "too_high" | "accurate" | "too_low" | string;
  reason: string;
  created_at: string | null;
};

export type MatchScoreCorrectionResult = {
  correction: MatchScoreCorrection;
  match: JobMatchReport;
};

export type AlertFeedbackInput = {
  alert_id: number;
  rating: AlertFeedbackRating;
  reason?: string;
  tags?: string[] | string;
};

export type RunScansInput = {
  company_id?: number;
  limit?: number;
  force?: boolean;
  dry_run?: boolean;
  trigger?: "manual" | "scheduled" | "command" | string;
};

export type RunScansResponse = {
  scanned: number;
  skipped: number;
  failed: number;
  alerts_created: number;
  due_count?: number;
  selected_count?: number;
  scan_jobs: ScanJob[];
  company?: Company;
  log?: CompanyLog;
};

export type CompanyLog = {
  id: number;
  company_id?: number;
  company_name?: string;
  company?: Pick<Company, "id" | "name">;
  status: "running" | "success" | "failed" | string;
  source_platform: string;
  jobs_found: number;
  jobs_created: number;
  jobs_updated: number;
  message: string;
  started_at: string | null;
  finished_at: string | null;
};

export type CompanyLogsQuery = {
  company_id?: number;
  limit?: number;
};

export type DiagnosticStatus = "ok" | "warning" | "error" | "unknown" | string;

export type DiagnosticCheck = {
  name: string;
  status: DiagnosticStatus;
  message?: string;
  detail?: unknown;
  checked_at?: string | null;
};

export type DiagnosticsResponse = {
  status?: DiagnosticStatus;
  generated_at?: string | null;
  checks?: DiagnosticCheck[];
  database?: DiagnosticCheck | Record<string, unknown> | string;
  worker?: DiagnosticCheck | Record<string, unknown> | string;
  scheduler?: DiagnosticCheck | Record<string, unknown> | string;
  ai?: DiagnosticCheck | Record<string, unknown> | string;
  smtp?: DiagnosticCheck | Record<string, unknown> | string;
  counts?: Record<string, number>;
  [key: string]: unknown;
};

export type NotificationPreferences = {
  id: number;
  quiet_hours_enabled: boolean;
  quiet_hours_start: string;
  quiet_hours_end: string;
  timezone: string;
  quiet_hours_active: boolean;
  digest_enabled: boolean;
  digest_frequency: "daily" | "weekdays" | "weekly" | string;
  digest_time: string;
  digest_channel: "local" | "email" | string;
  created_at: string | null;
  updated_at: string | null;
};

export type NotificationPreferencesInput = Partial<
  Pick<
    NotificationPreferences,
    | "quiet_hours_enabled"
    | "quiet_hours_start"
    | "quiet_hours_end"
    | "timezone"
    | "digest_enabled"
    | "digest_frequency"
    | "digest_time"
    | "digest_channel"
  >
>;

export type MatchApplyPriority = "apply_now" | "consider" | "stretch" | "ignore" | string;

export type JobMatchEvidence = {
  kind: string;
  message: string;
  values: string[];
};

export type JobMatchReport = {
  id: number;
  job_id: number;
  profile_id: number | null;
  source: "deterministic" | "agent" | string;
  overall_score: number;
  title_score: number;
  skill_score: number;
  seniority_score: number;
  location_score: number;
  confidence_score: number;
  knowledge_coverage_score: number;
  apply_priority: MatchApplyPriority;
  reasons_to_apply: string[];
  reasons_to_skip: string[];
  missing_skills: string[];
  evidence: JobMatchEvidence[];
  generated_at: string | null;
  updated_at: string | null;
};

export type JobRecord = {
  id: number;
  title: string;
  company: string;
  company_id: number;
  location: string;
  description: string;
  apply_url: string;
  source_url: string;
  source_platform: string;
  external_id: string;
  posted_at: string | null;
  tags?: string[];
  remote_policy: string;
  first_seen_at: string | null;
  last_seen_at: string | null;
  match: JobMatchReport;
  [key: string]: unknown;
};

export type ManualUrlInboxItem = {
  id: number;
  url: string;
  item_type: "unknown" | "company" | "job" | string;
  status: "pending" | "imported" | "dismissed" | string;
  title: string;
  notes: string;
  inferred_company: string;
  company_id: number | null;
  company_name: string;
  job_id: number | null;
  job_title: string;
  imported_at: string | null;
  dismissed_at: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type ManualUrlInboxInput = {
  url: string;
  item_type?: "unknown" | "company" | "job" | string;
  title?: string;
  notes?: string;
};

export type ExportedJob = JobRecord;

export type WorkspaceExport = {
  app_version?: string;
  generated_at: string;
  companies: Company[];
  jobs?: ExportedJob[];
  scan_logs?: CompanyLog[];
  scan_jobs?: ScanJob[];
  alerts?: JobAlert[];
  applications?: ApplicationRecord[];
  today_actions?: TodayAction[];
  profile?: CandidateProfile | null;
  alert_feedback?: AlertFeedback[];
  notification_preferences?: NotificationPreferences;
  job_matches?: JobMatchReport[];
  meta?: Record<string, unknown>;
  [key: string]: unknown;
};

export type WorkspaceImportResult = {
  status: "ok" | "partial" | string;
  imported: Record<string, number>;
  errors: Array<Record<string, unknown>>;
  error_count: number;
  domain_behavior: Record<string, string>;
};

export type DeletePersonalDataResult = {
  status: "ok" | string;
  deleted: Record<string, number>;
  confirmed_at: string;
};

export type CompanyImportCompany = {
  name?: string;
  careers_url: string;
  priority_tier?: PriorityTier;
  priority?: PriorityTier;
  title_keywords?: string[];
  negative_title_keywords?: string[];
  location_keywords?: string[];
  work_mode_filter?: WorkModeFilter;
};

export type CompanyImportPayload =
  | CompanyImportCompany[]
  | {
      companies?: CompanyImportCompany[];
      watchlist?: CompanyImportCompany[];
      company_watchlist?: CompanyImportCompany[];
      [key: string]: unknown;
    };

export type CompanyImportError = {
  index?: number;
  company?: string;
  careers_url?: string;
  error: string;
};

export type CompanyImportResult = {
  created?: number | Company[];
  updated?: number | Company[];
  created_count?: number;
  updated_count?: number;
  error_count?: number;
  skipped?: number;
  errors?: CompanyImportError[];
  message?: string;
  [key: string]: unknown;
};

export type ApiResult<T> =
  | {
      ok: true;
      data: T;
    }
  | {
      ok: false;
      error: Error;
    };
