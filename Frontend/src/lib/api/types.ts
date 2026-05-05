export type ApiResult<T> =
  | { ok: true; data: T }
  | { ok: false; error: Error };

export type ApiListResponse<T> = {
  count: number;
  results: T[];
};

export type BackendHealth = {
  status: "ok" | "error" | string;
  version?: string;
};

export type DiagnosticsResponse = {
  database: string;
  setup: {
    profile_complete: boolean;
    ai_configured: boolean;
    notifications_configured: boolean;
    company_watchlist_ready: boolean;
  };
  counts: {
    companies: number;
    active_companies: number;
    companies_needing_source: number;
    jobs: number;
    matches_to_notify: number;
    crawl_runs: number;
  };
};

export type PriorityTier = "dream" | "high" | "normal" | "fallback" | string;
export type SourceHealth =
  | "needs_setup"
  | "needs_source"
  | "needs_review"
  | "active"
  | "degraded"
  | "failing"
  | "paused"
  | "blocked"
  | string;
export type WorkModeFilter = "any" | "remote" | "hybrid" | "onsite" | string;
export type KeywordListValue = string[] | string | null;

export type CompanyJobSource = {
  id: number;
  company_id: number;
  url: string;
  source_type: string;
  platform: string;
  discovery_method: string;
  confidence_score: number;
  status: "active" | "needs_review" | "failed" | "disabled" | string;
  is_primary: boolean;
  evidence: Array<Record<string, unknown>>;
  notes: string;
  last_checked_at: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type Company = {
  id: number;
  name: string;
  domain: string;
  homepage_url: string;
  careers_url: string;
  priority: PriorityTier;
  priority_tier: PriorityTier;
  scraper_type: string;
  is_active: boolean;
  is_paused: boolean;
  state: "active" | "paused" | string;
  source_health: SourceHealth;
  source_discovery_status: string;
  source_discovery_confidence: number;
  source_discovery_notes: string;
  notes: string;
  primary_source: CompanyJobSource | null;
  sources: CompanyJobSource[];
  last_scraped_at: string | null;
  last_scrape_status: string;
  last_scrape_message: string;
  last_successful_scan_at: string | null;
  last_failed_scan_at: string | null;
  consecutive_failure_count: number;
  last_new_role_at: string | null;
  created_at: string | null;
  updated_at: string | null;
  title_keywords: KeywordListValue;
  negative_title_keywords: KeywordListValue;
  location_keywords: KeywordListValue;
  work_mode_filter: WorkModeFilter;
  scan_frequency_hours: number;
  alert_new_roles: boolean;
};

export type CreateCompanyInput = {
  name?: string;
  domain?: string;
  homepage_url?: string;
  careers_url?: string;
  priority_tier?: PriorityTier;
  is_active?: boolean;
  notes?: string;
};

export type UpdateCompanyInput = CreateCompanyInput & {
  scraper_type?: string;
  title_keywords?: string[];
  negative_title_keywords?: string[];
  location_keywords?: string[];
  work_mode_filter?: WorkModeFilter;
  scan_frequency_hours?: number;
  alert_new_roles?: boolean;
};

export type CompanyImportResult = {
  created_or_updated: number;
  errors: Array<Record<string, unknown>>;
  companies: Company[];
};

export type CompanyLog = {
  id: number;
  company_id: number;
  company_name: string;
  source_id: number | null;
  source_url: string;
  status: string;
  source_platform: string;
  jobs_found: number;
  jobs_created: number;
  jobs_updated: number;
  message: string;
  started_at: string | null;
  finished_at: string | null;
};

export type CrawlRun = {
  id: number;
  company_id: number;
  company_name: string;
  source_id: number | null;
  source_url: string;
  status: string;
  trigger: string;
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

export type CrawlResponse = {
  status: string;
  message: string;
  jobs_found: number;
  jobs_created: number;
  jobs_updated: number;
  company?: Company;
  log?: CompanyLog;
  crawl_run?: CrawlRun | null;
  alerts_created?: number;
};

export type RunCrawlsResponse = {
  scanned: number;
  skipped: number;
  failed: number;
  alerts_created: number;
  due_count: number;
  selected_count: number;
  crawl_runs: CrawlRun[];
};

export type JobMatch = {
  id: number;
  job_id: number;
  profile_id: number | null;
  source: string;
  overall_score: number;
  title_score: number;
  skill_score: number;
  seniority_score: number;
  location_score: number;
  confidence_score: number;
  knowledge_coverage_score: number;
  notification_threshold: number;
  should_notify: boolean;
  feature_snapshot: Record<string, unknown>;
  agent_summary: string;
  agent_review_status: string;
  model_version: string;
  apply_priority: "apply_now" | "consider" | "stretch" | "ignore" | string;
  reasons_to_apply: string[];
  reasons_to_skip: string[];
  missing_skills: string[];
  evidence: Array<Record<string, unknown>>;
  generated_at: string | null;
  updated_at: string | null;
};

export type JobRecord = {
  id: number;
  company_id: number;
  company_name: string;
  title: string;
  location: string;
  description: string;
  apply_url: string;
  source_url: string;
  source_platform: string;
  external_id: string;
  posted_at: string | null;
  tags: string[];
  remote_policy: string;
  status: string;
  first_seen_at: string | null;
  last_seen_at: string | null;
  created_at: string | null;
  updated_at: string | null;
  match: JobMatch;
};

export type MatchFeedbackInput = {
  feedback_type: string;
  notes?: string;
};

export type MatchFeedbackResult = {
  feedback: {
    id: number;
    job_id: number;
    match_id: number | null;
    profile_id: number | null;
    feedback_type: string;
    notes: string;
    created_at: string | null;
  };
  match: JobMatch;
};

export type UserSearchPreference = {
  id: number;
  minimum_match_score: number;
  minimum_confidence_score: number;
  match_strictness: "loose" | "balanced" | "strict" | string;
  preferred_seniority: string[];
  excluded_keywords: string[];
  excluded_companies: string[];
  feedback_weights: Record<string, number>;
};

export type CandidateProfile = {
  id: number;
  full_name: string;
  headline: string;
  location: string;
  remote_preference: string;
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
  search_preferences: UserSearchPreference;
  target_titles: TargetTitle[];
  claims: ProfileClaim[];
  search_strategy: SearchStrategy;
};

export type CandidateProfileInput = Partial<CandidateProfile> & {
  github_url?: string;
  linkedin_url?: string;
  portfolio_url?: string;
};

export type TargetTitle = {
  id: number;
  title: string;
  fit_bucket: string;
  confidence_score: number;
  knowledge_accuracy: number;
  evidence: Array<Record<string, unknown>>;
  source: string;
  status: string;
};

export type ProfileClaim = {
  id: number;
  claim_type: string;
  text: string;
  evidence: string;
  source: string;
  status: string;
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
};

export type NotificationPreferences = {
  id: number;
  quiet_hours_enabled: boolean;
  quiet_hours_start: string;
  quiet_hours_end: string;
  timezone: string;
  quiet_hours_active: boolean;
  digest_enabled: boolean;
  digest_frequency: string;
  digest_time: string;
  digest_channel: string;
  email_address: string;
  immediate_email_enabled: boolean;
  minimum_match_score: number;
  minimum_confidence_score: number;
  max_digest_items: number;
};

export type NotificationPreferencesInput = Partial<NotificationPreferences>;

export type AgentProvider = {
  id: number;
  provider: string;
  label: string;
  model_name: string;
  enabled: boolean;
  worker_only: boolean;
  api_key_env_var: string;
  api_key_configured: boolean;
  default_tool_policy: string;
  consent_required: boolean;
  daily_run_limit: number;
  monthly_budget_cents: number;
  estimated_cost_per_run_cents: number;
  notes: string;
};

export type AgentRuntimeStatus = {
  execution_mode: string;
  queue_batch_size: number;
  queued_runs: number;
  running_runs: number;
  providers: Array<Record<string, unknown>>;
};

export type AgentRun = {
  id: number;
  agent_type: string;
  status: string;
  provider: string;
  model_name: string;
  tool_policy: string;
  prompt_version: string;
  result_summary: string;
  error: string;
  user_safe_error: string;
  requested_at: string | null;
  started_at: string | null;
  finished_at: string | null;
  steps: Array<Record<string, unknown>>;
  artifacts: Array<Record<string, unknown>>;
  decisions: Array<Record<string, unknown>>;
};

export type StartAgentRunInput = {
  agent_type: string;
  provider?: string;
  tool_policy?: string;
  user_consent?: boolean;
};
