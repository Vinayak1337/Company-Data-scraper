# V3 Plan

## Product Thesis

V3 is a profile-first company watchlist that discovers career sources, crawls active companies, matches new jobs to the user's profile, and notifies the user only when a role is worth reviewing.

The product should feel smaller than V2. Every screen and backend module should support one of these outcomes:

1. The user finishes profile, AI, and notification setup.
2. The user imports companies from CSV and controls which companies are active.
3. The system finds and verifies each company's public jobs source.
4. A local terminal command crawls due active sources and normalizes jobs. Hosted scheduling comes after the local loop is proven.
5. The system uses deterministic scoring plus agentic AI review to decide match quality.
6. The system notifies the user with useful match explanations.
7. The user gives feedback so future notifications become stricter or looser.

## V3 User Flow

### 1. Setup

The user starts on a setup checklist, not a dashboard.

Required setup:

- Profile identity: name, headline, location.
- Profile substance: resume text, skills, target titles, seniority, preferred work modes, target locations, dealbreakers.
- AI runtime: provider, model, key/env readiness, run limits, consent requirement, and whether the provider is local-only. Provider setup belongs to the terminal CLI, not Settings.
- Notification settings: email address, digest frequency, minimum match score, confidence threshold, quiet hours.

The app can show data before setup is complete, but recurring matching and notifications should remain disabled until the required setup gates pass. V3 starts local-first: `./scripts/job-scout setup` collects setup data, `./scripts/job-scout providers` chooses the local brain provider and writes `Backend/.env`, and the web UI only reports provider readiness before the app is treated as production-ready.

### 2. Company Watchlist Import

The user uploads a CSV with any of these columns:

- `company`
- `name`
- `domain`
- `homepage_url`
- `careers_url`
- `priority`
- `active`
- `notes`

Import behavior:

- Deduplicate by normalized domain, homepage URL, careers URL, then company name.
- Create inactive or active watchlist items based on CSV values, defaulting to active.
- If `careers_url` is present, store it as a manual/primary source.
- If only company/domain is present, queue source discovery.
- Return per-row errors instead of rejecting the whole file.

### 3. AI Careers Source Discovery

For each company without a usable jobs source:

- Build a search query from company name and domain.
- Prefer public ATS/source patterns: Greenhouse, Lever, Ashby, Workday, SmartRecruiters, Microsoft Careers, company `/careers`, `/jobs`, `/open-roles`.
- Store candidate sources with confidence and discovery notes.
- Mark high-confidence sources active automatically.
- Mark low-confidence sources as `needs_review`.
- Allow manual URL override.

This can start as a local deterministic agent adapter and later call an LLM/search runtime. The database should already represent agent decisions, confidence, and auditability.

### 4. Local Periodic Crawling

A terminal command runs due active companies:

- Select companies with at least one active source whose scan cadence is due.
- Crawl the primary source.
- Normalize jobs into a stable `Job` record.
- Deduplicate by company plus apply URL, external ID, or normalized title/location/source.
- Update `last_seen_at` for still-open jobs.
- Mark missing jobs as stale/closed after repeated absence.
- Record each crawl run with counts, status, error, and duration.
- Create match notification events after crawls before sending queued emails.

The command path is local-first:

```bash
./scripts/job-scout run-once --force
python manage.py run_periodic_maintenance --scan-limit 25 --notification-limit 25
```

Hosted cron, uptime pings, or worker deployment should be added only after this local command produces correct crawl, match, and email behavior.

### 5. Matching

Every new or updated job should be matched against the profile.

The first implementation uses an interpretable ML-style scorer:

- Extract features for title overlap, skill coverage, seniority fit, location/work-mode fit, negative keyword hits, dealbreaker hits, profile completeness, and source confidence.
- Combine features with tunable weights.
- Apply user feedback as lightweight preference learning.
- Produce an overall score, confidence score, threshold recommendation, apply priority, reasons to apply, reasons to skip, missing skills, and evidence.

The agentic layer reviews the structured score:

- It can raise/lower confidence when evidence is thin or contradictory.
- It can decide the notification threshold for each job.
- It can explain why a role is above or below the user's current preferences.
- It must preserve evidence and avoid opaque "AI says so" results.

### 6. Notifications

Notifications should be sent only for useful matches.

Email content:

- Company and title.
- Match score and confidence.
- Why this is a match.
- What may be missing.
- Apply URL.
- Controls: save, dismiss, too strict, too loose, wrong role, wrong location, wrong seniority.

Digest rules:

- Immediate, daily, weekly, or disabled.
- Minimum score threshold.
- Minimum confidence threshold.
- Maximum items per digest.
- Do not resend the same job unless the score materially changes.

### 7. Feedback Tuning

User feedback should become product behavior, not just analytics.

Feedback types:

- `good_match`
- `bad_match`
- `too_senior`
- `too_junior`
- `wrong_location`
- `wrong_role`
- `missing_skill`
- `not_interested_company`
- `too_many_notifications`
- `want_more_matches`

Feedback effects:

- Adjust user preference weights.
- Adjust minimum score/confidence thresholds.
- Add negative keywords or company-level exclusions when repeated.
- Improve explanations by preserving feedback in future match evidence.

## Target Backend Modules

Keep:

- `profiles`: candidate profile, search preferences, setup readiness.
- `companies`: watchlist, job sources, crawl runs, crawl status, CSV import.
- `jobs`: normalized discovered jobs.
- `matching`: ML-style scoring, AI review payloads, feedback events.
- `notifications`: email/digest preferences, notification records.
- `agents`: provider settings, run audit, source discovery and match review adapters.
- `api`: small JSON API for the V3 frontend.
- `scrapers_engine`: source-specific and generic job extraction.
- `api.management.commands.job_scout`: local setup/status/run-once CLI.

Remove from V3:

- `applications`: application CRM is not required for source discovery and notifications.
- `interviews`: interview prep is post-match workflow and should wait.
- `analytics`: broad analytics dashboards are not needed before feedback-driven matching works.
- `intelligence`: company intelligence is not needed for the core loop.
- `discovery`: manual URL inbox is replaced by company source discovery.
- `dashboard`: legacy Django templates duplicate the Next app.

## Target Frontend Screens

Keep and reshape:

- `Today`: setup checklist, due companies, best new matches, latest crawl runs.
- `Profile`: profile setup and target preferences.
- `Companies`: CSV import, watchlist table, source status, active/inactive toggles, run now.
- `Jobs`: match inbox with score explanations and feedback controls.
- `Settings`: AI provider readiness, email/digest preferences, thresholds, data controls.

Remove:

- `Applications`
- `Analytics`
- Separate `Agents` top-level page
- Manual URL inbox UX
- Company intelligence UX

## Data Model Direction

Core tables:

- `CandidateProfile`
- `UserSearchPreference`
- `Company`
- `CompanyJobSource`
- `CrawlRun`
- `Job`
- `JobMatch`
- `MatchFeedback`
- `NotificationPreference`
- `NotificationEvent`
- `AgentProviderSetting`
- `AgentRun`

Compatibility note:

- V2 uses `ScanJob`. V3 should expose "crawl run" language in product/UI. The implementation may keep old table names during migration only if a direct rename is risky, but new docs/API should use crawl terminology.

## Implementation Phases

### Phase 1: Cut Scope and Document

- Commit V2 and branch V3.
- Create `docs/v3-plan.md`.
- Create `docs/design.md`.
- Remove out-of-scope backend apps from Django settings.
- Remove out-of-scope frontend pages/navigation.
- Replace broad API surface with V3 endpoints.

### Phase 2: Watchlist and Source Discovery

- Add `CompanyJobSource`.
- Allow company creation from CSV with name/domain/homepage/careers URL.
- Add source discovery statuses and confidence.
- Add deterministic source discovery service.
- Add manual source override.
- Update company serializers and frontend companies page.

### Phase 3: Crawling

- Rename or reshape scan concepts into crawl runs.
- Crawl only active companies with active sources.
- Persist crawl status, counts, source URL, and errors.
- Add "run now" and "run due" actions.

### Phase 4: Matching and Feedback

- Expand `JobMatch` with feature payloads, threshold recommendation, notification decision, and agent review status.
- Add `MatchFeedback`.
- Replace V2 deterministic matching with weighted feature scoring.
- Use feedback to adjust match behavior.
- Add agent runtime adapter for match review.

### Phase 5: Notifications

- Expand notification preferences for email/digest thresholds.
- Add `NotificationEvent`.
- Create digest generation service.
- Add email backend integration with dry-run/local mode.
- Ensure duplicate suppression.

### Phase 6: Verification

- Backend tests for CSV import, source discovery, crawl run, scoring, feedback, and notification selection.
- Frontend lint/build.
- API smoke tests.
- Minimal local run instructions.
- Local setup CLI checks for profile, watchlist, notifications, providers, and CLI-only runtime guards. Provider selection must work through a terminal menu.

## Non-Goals

Do not add these in V3:

- Auto-apply.
- Resume tailoring.
- Cover letter generation.
- Interview prep.
- Hosted CLI execution. CLI providers require a locally logged-in terminal and must stay out of hosted web/runtime services.
- Offer support.
- Recruiter/contact research.
- Large analytics dashboards.
- Browser extension.
- Multi-user/team admin unless authentication becomes explicit product scope.
- Hidden autonomous external actions without consent and audit logs.

## Quality Rules

- No ghost modules, pages, or endpoints after the V3 cut.
- Prefer a small API surface with stable names.
- Make AI decisions inspectable: score, confidence, evidence, threshold, and reason.
- Every periodic action must have a run record.
- Every notification must be deduplicated and auditable.
- Feedback must change future behavior.
- Keep generated local artifacts ignored and out of git.
