# Job Scout v2 Plan

## Product Direction

Build a developer-centric, self-hosted company job tracker that is easy to run locally or deploy on Render. V1 answers "what jobs exist at my tracked companies?" V2 should answer "did any of my favorite companies post a role I should care about, how urgent is it, and what should I do next?"

The product should remain plug-and-play:

- One-command local setup.
- Simple deploy path.
- User-owned data.
- No required AI key for basic scraping/tracking.
- Optional Gemini/OpenAI integration for resume parsing, profile generation, matching, and writing assistance.

## Review Decisions And Clarifications

This plan has been reviewed for ambiguity, low-value features, engineering controls, and delivery risk. The decisions below override any vague wording elsewhere in the document.

Product boundary:

- Target user: one developer tracking a personal watchlist of favorite companies.
- Primary value: preventing missed roles at companies the user already cares about.
- Secondary value: ranking tracked-company jobs by fit and producing clear next actions.
- Not a recruiting CRM.
- Not a public SaaS marketplace.
- Not an autonomous job-application bot.
- Not a LinkedIn scraper.
- Not a tool for fabricating CV claims.

North star:

- The product exists to make sure a user does not miss relevant openings from companies they intentionally track.
- Job boards are discovery-first. Job Scout should be watchlist-first.
- Resume-aware matching, AI agents, CV tailoring, analytics, and recruiter intelligence are support layers around the company-tracking loop.
- If a feature does not improve company tracking, alert quality, role prioritization, or application readiness, it should not be core.

Architecture decision:

- Frontend: Next.js for the v2 application UI.
- Backend: Django/Python API and domain backend.
- Workers: Python background workers for scraping, AI agents, scheduled scans, PDF/CV generation, and long-running workflows.
- Database: Postgres for deployed use; SQLite can remain supported for local development.
- Queue/cache: Redis or equivalent when background concurrency is needed.
- V1 Django templates/HTMX can stay as the legacy/simple version; v2 should move to a richer Next.js frontend because the product is UI- and workflow-heavy.

AI decision:

- AI is optional for basic scraping and tracking.
- AI is required for advanced profile generation, title generation, match explanations, tailoring, and agent workflows.
- The app must work in degraded mode when no AI key is configured.
- Every AI-generated profile claim must be confirmable by the user before it is used in a CV, application, or recruiter message.

Scoring decision:

- Scores are guidance, not truth.
- Every score must include evidence and uncertainty.
- Prefer buckets over fake precision: Strong Fit, Good Fit, Stretch, Weak Fit.
- If evidence is missing, the system should say "unknown" rather than guessing.

Source decision:

- ATS APIs and public careers pages are first-class sources.
- Authenticated job boards and private pages are out of scope unless the user manually saves a job URL/content.
- Recruiter intelligence is public-data-only and should be presented as contact hints, not a people database.

Source governance:

- Every scraper adapter needs a named source owner in code/docs.
- Every new source needs a terms/robots/rate-limit review before being enabled by default.
- Default scan cadence must be conservative.
- Failed or blocked sources should degrade gracefully, not break the whole scan.
- If a source asks not to be scraped or blocks requests, the app should disable that source and show a clear status.
- The app should prefer official ATS/public APIs where available.

## Product Success Criteria

The product should be judged by whether it prevents missed opportunities at tracked companies and helps the user act quickly on the right ones.

User success metrics:

- Time from first run to first tracked company scan.
- Number of favorite companies successfully tracked.
- Number of relevant new roles detected from tracked companies.
- Time between company posting and user alert.
- Ratio of useful tracked-company alerts to noisy alerts.
- Number of missed relevant roles discovered late.
- Number of applications submitted from tracked-company alerts.
- Follow-up tasks completed on time.
- User corrections to match scores decrease over time.
- User can explain why a job is recommended from evidence shown in the UI.

Product quality metrics:

- Onboarding completion rate.
- Profile completeness score.
- Company watchlist setup completion rate.
- Scan success rate by source.
- Company source health rate.
- Duplicate/repost detection accuracy.
- Match feedback correction rate.
- Agent run success rate.
- Export/import success rate.
- No-AI mode completion for scraping/tracking/manual profile management.

Engineering success metrics:

- Core pages load quickly on local hardware.
- Long-running jobs never block request/response paths.
- Failed scans and failed agent runs are visible and recoverable.
- User data can be exported before risky migrations.
- Critical workflows have automated tests.

## Value Strategy And Product Positioning

This project is not valuable if it only becomes another job-board aggregator. Users can already search jobs, save searches, set alerts, upload resumes, and track some applications on major job boards. The product must create value in the gap between "I care about these companies" and "I know immediately when one of them posts a relevant role."

Core value proposition:

- Favorite-company job tracking across ATS and careers pages.
- Reliable new-role detection and alerting.
- Company-level scan health, so users know whether tracking is working.
- Cross-source personal job intelligence for developers.
- Evidence-backed fit scoring from the user's real CV/profile/projects.
- Daily action queue that prioritizes the next useful action.
- Truthful CV/application tailoring based on confirmed proof points.
- Search strategy learning from user feedback and outcomes.
- Local-first data ownership and bring-your-own AI.

The product should compete on:

- Reliability of tracked-company monitoring.
- Speed and usefulness of company-specific alerts.
- Quality of targeting.
- Reduction of irrelevant jobs.
- Application readiness.
- Follow-up discipline.
- User-owned workflow.
- Explainability.

The product should not compete on:

- Largest job database.
- One-click mass apply.
- Social networking.
- Recruiter marketplace.
- Employer-side tools.
- Generic job search SEO.

Positioning statement:

> "A self-hosted company job radar for developers that watches your favorite companies, detects new roles across their career pages and ATS platforms, and turns relevant openings into prioritized next actions."

## Competitive Baseline

Current job boards already provide important primitives:

- Search and filters.
- Saved searches.
- Email/app job alerts.
- Resume/profile storage.
- Saved jobs.
- Some application tracking.

This means v2 must not spend most of its effort rebuilding generic search UI. The wedge is deeper personal context and workflow control.

Differentiation:

- Job boards ask "what did you search for?"
- Job Scout should ask "which companies do you care about, did they post anything new, and is this role worth acting on?"

Job boards optimize for broad discovery and marketplace activity. Job Scout should optimize for watchlist coverage, alert reliability, decision quality, and application quality.

## Anti-Noise Principles

The biggest product risk is adding more jobs to an already noisy search. The app must actively prevent that.

Rules:

- Do not show every scraped job by default.
- Default view should be tracked companies with new/changed relevant roles.
- Daily Action Queue should prioritize favorite-company roles first.
- Jobs with weak fit should be collapsed into review/ignore buckets.
- Alerts should fire only for meaningful opportunities.
- Every recommended job needs a reason and evidence.
- Every skipped job should have a clear skip reason when possible.
- The user should be able to mark "not relevant" quickly.
- Feedback must update future filters and recommendations.

Success means the user applies to fewer, better jobs with more confidence.

## Business Planning Without Monetization

Even if this is not being built to sell, use business planning to make sure it is worth trying.

Value hypotheses:

- Developers do not primarily need more job listings; they need to stop missing roles at companies they care about.
- A company watchlist is more emotionally and practically useful than another global search feed.
- Source health matters: users need confidence that a company is actually being monitored.
- Resume-aware role generation helps users discover titles they would not search manually.
- Evidence-backed match explanations increase trust and reduce wasted applications.
- A daily action queue improves consistency more than another job list.
- Local-first data ownership and bring-your-own AI are meaningful differentiators for technical users.

Validation plan:

1. Dogfood with one real developer profile and 25-50 favorite companies.
2. Track whether each company source can be scanned successfully.
3. Measure time from company posting to app detection.
4. Measure alert usefulness: relevant, maybe, irrelevant.
5. Manually inspect whether relevant alerts are better than saved job-board searches.
6. Run profile/title generation and check whether generated titles improve company alerts.
7. Use the app to prepare 5 applications from tracked-company alerts and compare effort/time against doing it manually.
8. Track whether the user submits fewer low-quality applications.
9. Track whether follow-ups and interview prep happen more reliably.

Pass/fail signals:

- Pass: user finds jobs they would have missed or misunderstood.
- Pass: user catches a role at a favorite company faster than manual checking.
- Pass: user trusts source health enough to stop manually checking every company page.
- Pass: user rejects noisy jobs faster.
- Pass: user can produce better tailored materials faster.
- Pass: user trusts match explanations because they cite real evidence.
- Fail: app mostly shows the same jobs as LinkedIn/Indeed without better prioritization.
- Fail: tracked company scans are unreliable or opaque.
- Fail: users still feel they must manually check each favorite company's career page.
- Fail: app encourages more applications without improving quality.
- Fail: AI suggestions require too much correction.
- Fail: setup/maintenance costs more time than it saves.

## Career-Ops Inspirations To Borrow

Useful ideas from `career-ops` that should influence v2:

- User layer vs system layer separation.
- `cv.md` as canonical source of truth.
- `profile.yml` for identity, target roles, compensation, and preferences.
- `_profile.md` style narrative/archetype customization.
- Proof point library from projects, articles, and work history.
- Job evaluation reports with role summary, CV match, gaps, level strategy, personalization plan, and interview prep.
- Application tracker.
- Follow-up cadence.
- Story bank for reusable STAR+R interview stories.
- Batch evaluation for multiple jobs, but only after deterministic filtering.
- Pattern analysis to learn from rejections, saves, and user feedback.

What not to copy blindly:

- Command-heavy UX. V2 should expose these workflows through a polished web app.
- Generating PDFs before the match/application decision is clear.
- Running deep AI analysis on every job. Use deterministic filtering first.
- Broad multilingual/multi-mode complexity before the core developer workflow works.

## Primary Personas And Jobs To Be Done

Primary persona:

- A developer running the app for their own job search.
- Comfortable with local setup, Git, env vars, and deployment guides.
- Wants control over data and AI keys.
- Wants fewer irrelevant jobs and clearer application decisions.

Secondary persona:

- A developer who is less comfortable with setup but can follow a one-command script and deploy guide.
- Needs good defaults, clear diagnostics, and exportable data.

Jobs to be done:

- "When I start a job search, help me turn my background into a clear target-role strategy."
- "When new jobs appear, show me which ones are actually worth my time."
- "When I find a job manually, let me save and evaluate it quickly."
- "When I decide to apply, help me tailor truthful materials based on my real experience."
- "When I have active applications, remind me what to follow up on and how to prepare."
- "When my search is noisy, tell me what to change."

## Information Architecture

The full app should be organized around workflows, not a generic dashboard.

Primary navigation:

- Today: daily action queue, urgent jobs, follow-ups, failed scans.
- Jobs: discovered jobs, filters, match scores, saved searches.
- Companies: watchlist, sources, scan status, company tiers.
- Profile: CV, profile, proof points, skills, generated titles.
- Applications: pipeline, artifacts, follow-ups, interview prep.
- Agents: runs, approvals, artifacts, permissions.
- Analytics: search quality, source quality, missing skills, outcomes.
- Settings: AI providers, SMTP, schedules, data, diagnostics.

Critical screens:

- Onboarding wizard.
- Profile editor.
- Claim confirmation queue.
- Generated job-title review.
- Job list with match evidence.
- Job detail and match report.
- Application workspace.
- Daily action queue.
- Agent run detail.
- Scan diagnostics.
- Data export/import.

State design:

- Every async operation needs empty, loading, success, partial-success, failed, retrying, and cancelled states.
- Every AI-generated artifact needs draft, needs review, approved, rejected, and superseded states.
- Every external source needs healthy, degraded, failing, disabled, and needs attention states.

## Migration From V1

V2 should not discard useful v1 data.

Migration goals:

- Import existing companies.
- Import existing jobs.
- Preserve scraper source metadata where possible.
- Preserve manual filters as saved searches where possible.
- Add generated v2 fields without forcing all users through destructive migrations.

Migration steps:

1. Add export command to v1 data if needed.
2. Define v2 import format.
3. Map v1 `Company` records to v2 company/source records.
4. Map v1 `Job` records to v2 job records.
5. Mark imported records with source `v1-import`.
6. Run dedupe after import.
7. Ask user before deleting or overwriting old data.

Migration acceptance:

- User can run v2 against a fresh database.
- User can import v1 data.
- Failed imports produce a readable report.
- Original v1 database remains untouched unless the user explicitly chooses otherwise.

## Security And Threat Model

Even single-user self-hosted apps need security because this app handles resumes, emails, API keys, and job-search history.

Authentication and access:

- Deployed v2 must require login by default.
- Local development can allow a simplified single-user mode.
- Session security, CSRF protection, CORS restrictions, and secure cookies must be configured.
- Admin endpoints and diagnostics must not be public.

Secrets:

- AI keys, SMTP credentials, database URLs, and webhook secrets must be stored as environment variables or encrypted settings.
- Secrets must never be logged, exported by default, or sent to AI providers.
- Diagnostics should show whether a secret is configured, not the secret value.

User-submitted URLs:

- Treat all URLs as untrusted.
- Validate schemes and hosts.
- Block local/private network targets by default to reduce SSRF risk.
- Enforce request timeouts, redirects limits, size limits, and user-agent policy.

File uploads:

- Validate file type and size.
- Store uploads outside executable paths.
- Parse PDFs/documents defensively.
- Never execute uploaded content.

Prompt injection:

- Treat job descriptions, scraped pages, READMEs, and websites as untrusted text.
- Never let scraped content override system instructions.
- Agent tools must use fixed tool permissions, not permissions suggested by job content.
- AI outputs that would change user data must go through approval.

External actions:

- No automatic applying.
- No automatic outreach.
- No automatic profile publishing.
- No external message is sent without user confirmation.

## AI Quality And Evaluation

AI features need evaluation before they are trusted.

Evaluation datasets:

- Sample resumes/profiles.
- Sample job descriptions across frontend, backend, full-stack, AI, DevOps, data, mobile, and QA.
- Known-good target title outputs.
- Known-good match reports.
- Known-bad hallucination cases.
- Scraped noisy/malformed job descriptions.

Evaluation checks:

- Does the generated title list match the user's actual evidence?
- Does every match claim cite CV/profile/job evidence?
- Does the system mark unknowns instead of guessing?
- Does the system avoid inventing skills?
- Does feedback change future ranking in a predictable way?
- Does no-AI mode still support the manual workflow?

Prompt and model versioning:

- Store prompt version with every agent run.
- Store model/provider used.
- Store input snapshot and output artifact.
- Support re-running an agent with a newer prompt/model without overwriting old artifacts.

Cost controls:

- Show estimated AI cost/token use for agent runs when available.
- Add per-run and daily AI budget limits.
- Avoid deep AI review for every scraped job; use deterministic filtering first.
- Run expensive AI workflows only for shortlisted jobs or explicit user actions.

## Operational Readiness

The app needs operational planning before implementation.

Observability:

- Structured logs for API requests, scan runs, worker jobs, agent runs, and alerts.
- Privacy-safe logs: no full resumes, secrets, or full AI prompts in normal logs.
- Error tracking for failed scans, failed agents, failed emails, and import/export failures.
- Metrics for scan duration, worker queue depth, source success rate, and AI failures.

Reliability:

- Background jobs must be idempotent where possible.
- Jobs need retry limits and dead-letter/failure states.
- Scheduler must avoid overlapping scans for the same source.
- Long scans must be cancellable.
- Partial scan results should be saved when safe.

Performance:

- Job list and match filters need indexes.
- Large job lists need pagination or virtualized UI.
- Scraper responses need size/time limits.
- Agent history should be paginated.

Backup and recovery:

- User can export all data.
- User can import exported data into a fresh install.
- Before destructive migrations, app should recommend or trigger export.
- Failed migrations/imports should produce a recovery report.

Deployment:

- Provide local dev instructions.
- Provide Render deployment instructions.
- Provide environment variable template.
- Provide diagnostics for worker, scheduler, database, AI provider, and SMTP.
- Docker support is useful but should not block P0 unless chosen as the deployment baseline.

## Core User Flow

1. User starts the app.
2. User adds favorite companies or imports a company watchlist.
3. App detects the company's careers/ATS source and verifies scan health.
4. User optionally creates/imports a developer profile to improve filtering.
5. App generates target titles and alert rules from the profile/preferences.
6. Scheduled scans check tracked companies for new, changed, or reposted roles.
7. User gets alerts and a Today queue when favorite companies post relevant roles.
8. User reviews relevant roles, saves/applies/skips, and tracks applications.
9. App learns from feedback and improves future company alerts.

## User Profile Layer

Inspired by `career-ops`, v2 should separate user-owned profile data from system logic.

User-owned data:

- `cv.md`: canonical markdown CV.
- `profile.yml`: identity, location, links, target roles, compensation, preferences.
- `profile.md`: detailed career narrative, strengths, deal-breakers, proof points, and target role framing.
- `proof_points.md`: project metrics, portfolio links, STAR stories, articles, demos.
- `applications.md` or database equivalent: application tracker.
- `scan_history`: known jobs, duplicates, reposts, and alert history.

In the web app, these can live in database tables, but import/export should preserve this shape so developers can edit files in git if they prefer.

## Onboarding

V2 onboarding should start with company tracking. Profile setup comes immediately after because it improves alert quality.

Required:

- Add at least one company URL or company name.
- Detect and verify the company's careers/ATS source.
- Choose alert channel and scan frequency.
- Set role/title keywords.
- Set location and remote/hybrid/onsite preferences.

Recommended:

- Paste/upload resume or CV.
- Convert resume to clean markdown CV.
- Ask for full name, email, location, timezone, links, and work authorization.
- Ask target geographies and remote/hybrid/onsite preferences.
- Ask compensation expectations and minimum threshold.
- Ask what roles the user wants.
- Ask what roles the user does not want.
- Ask strongest skills, weak skills, and skills they want to grow into.
- Ask deal-breakers: location, company size, industry, tech stack, contract type.
- Ask best proof points: shipped products, open source, metrics, leadership, projects.
- Ask "what makes you different from other developers?"

The onboarding output should be:

- A working company watchlist.
- Source health status for tracked companies.
- Initial alert rules.
- Manual role/title, location, and work-mode filters.
- Optional normalized `cv.md`.
- Optional structured `profile.yml`.
- Optional generated `profile.md` with archetypes, narrative, role preferences, and proof points.
- Optional generated target-role map.

## Company Watchlist

The watchlist is the core product object.

For each tracked company, store:

- Company name.
- Priority tier: dream, high, normal, fallback, paused.
- Careers URL.
- Detected ATS/source type.
- Source health status.
- Last successful scan.
- Last failed scan.
- Last new role detected.
- Scan frequency.
- Alert rules.
- Role/title filters.
- Location/work-mode filters.
- Notes.

Company states:

- Active: scanning successfully.
- Needs setup: no valid source yet.
- Degraded: source works but has partial failures.
- Failing: scan repeatedly fails.
- Paused: user disabled scanning.
- Blocked: source blocks scraping or should not be scanned.

Company watchlist views:

- New roles.
- Favorites with new roles.
- Failing sources.
- No recent openings.
- Paused companies.

Company acceptance criteria:

- User can add a company by URL.
- User can add a company by name and then confirm detected URL.
- App shows whether the company is being tracked successfully.
- User can pause, edit, delete, and manually rescan a company.
- Failed company scans show readable reasons and suggested fixes.

## Developer Portfolio Import

Because this is developer-centric, the app should understand more than a resume.

Supported inputs:

- GitHub profile URL.
- Portfolio URL.
- LinkedIn URL or exported profile text.
- Project README files.
- Personal website project pages.
- Existing `cv.md`, `profile.yml`, and `profile.md` files.

Outputs:

- Project proof points.
- Technical skill inventory.
- Role-aligned project highlights.
- Portfolio gaps.
- Resume bullet suggestions.
- Interview story seeds.

The app should not blindly trust imported data. It should ask the user to confirm generated skills, metrics, and project claims before using them in CVs or applications.

## AI-Generated Target Job Titles

Add a profile analysis step that generates job titles the user can apply for based on their resume/profile.

For each generated title, store:

- Job title.
- Role family: frontend, backend, full-stack, mobile, platform, DevOps, AI, data, security, QA, developer relations, technical support, solutions, etc.
- Level: intern, junior, mid, senior, staff, lead.
- Fit score.
- Confidence score.
- Knowledge accuracy score: how much of the required knowledge is already evidenced in the CV/profile.
- Evidence: exact CV/profile proof points used.
- Gaps: missing skills or weaker areas.
- Search keywords and synonyms.
- Negative keywords to avoid.
- Example companies/teams where the title fits.

The score should not pretend to be exact. Use clear buckets:

- Strong Fit: enough direct evidence to apply confidently.
- Good Fit: mostly aligned, minor gaps.
- Stretch: plausible but needs targeted resume/project framing.
- Weak Fit: not recommended unless the user wants a transition path.

This generated title list should drive:

- Default filters.
- Company scan keywords.
- Job alert rules.
- Resume tailoring.
- Gap analysis.

## Matching Engine

Every job should be evaluated against the user's profile.

Outputs per job:

- Overall match score.
- Role/title fit.
- Skill coverage.
- Seniority fit.
- Location fit.
- Compensation fit when available.
- Company/domain fit.
- Posting legitimacy.
- Apply priority: apply now, consider, stretch, ignore.
- Reasons to apply.
- Reasons to skip.
- Missing skills and mitigation plan.

Use deterministic matching first:

- Title keywords.
- Skill keywords.
- Location and work mode.
- Seniority terms.
- User preferences and deal-breakers.

Use AI optionally for:

- Resume/profile extraction.
- Job title generation.
- Messy job description parsing.
- Match explanation.
- Gap mitigation.
- Tailored CV summary.
- Outreach/application drafts.

## Agentic AI Workflows

V2 should include agentic workflows, but they must be controlled, reviewable, and task-based. The goal is not to build an autonomous bot that applies to jobs. The goal is to reduce research, matching, tailoring, follow-up, and search-strategy work while keeping the user in control.

Agent rules:

- Agents can research, draft, score, organize, and suggest.
- Agents cannot apply to jobs automatically.
- Agents cannot contact recruiters automatically.
- Agents cannot invent resume claims, fake skills, fake metrics, or fake credentials.
- Agents must cite the profile/CV/job evidence behind important recommendations.
- Agents must ask for confirmation before changing user-owned profile/CV data.
- Agents must store every run with inputs, outputs, status, and user decision.
- Agents must be interruptible, retryable, and safe to rerun.

Architecture:

- Next.js UI starts and reviews agent runs.
- Django API owns agent state, orchestration, permissions, data access, runtime selection, and persistence.
- Python workers execute long-running agent tasks and runtime adapter calls.
- Database stores agent runs, steps, artifacts, decisions, and logs.
- UI polls or streams progress from the backend.

Do not run serious agent workflows inside serverless request handlers. Scraping, profile analysis, multi-step matching, PDF generation, and weekly strategy review should run as durable backend jobs.

### Django Agent Orchestrator And Runtime Router

The Agent Orchestrator is part of the main v2 backend plan. It is not a separate AI shell app. Django owns the workflow state, permissions, audit trail, artifacts, and user-facing results. External CLIs and model APIs are runtime adapters only.

Control flow:

```text
Django Agent Orchestrator
  -> Runtime adapter:
      1. Gemini CLI
      2. Claude Code CLI
      3. OpenCode
      4. Direct API providers
      5. OpenRouter / DeepSeek / other providers
  -> Tool policy / permissions
  -> Audit logs + artifacts
  -> User-facing result
```

Responsibilities:

- Validate the requested agent run and input snapshot.
- Select the runtime provider and model for the agent type.
- Enforce tool policy before any runtime sees user, job, profile, or scraped content.
- Dispatch execution to a worker queue.
- Store step logs, prompts, model/provider metadata, runtime output, artifacts, errors, token/cost estimates when available, and user decisions.
- Support cancellation, retry, approval gates, and safe reruns.
- Return a reviewable result to the Next.js UI.

Runtime adapters:

- `direct_api`: direct model API calls for structured, low-risk tasks.
- `openrouter`: hosted model routing for cheaper model experiments.
- `deepseek`: direct or routed DeepSeek provider support.
- `gemini_cli`: worker-only CLI execution for Gemini CLI workflows.
- `claude_code_cli`: worker-only CLI execution for Claude Code CLI workflows.
- `opencode`: worker-only OpenCode execution for provider-router workflows.

Adapter contract:

```text
prepare(context, policy) -> invocation_payload
execute(invocation_payload) -> runtime_result
collect_artifacts(runtime_result) -> artifacts
summarize_failure(error) -> user_safe_error
```

Tool policy levels:

- `read_only`: may read approved app context only.
- `workspace_write`: may create draft artifacts only.
- `safe_shell`: may run allowlisted commands only in an isolated temporary workspace.
- `network_tools`: disabled by default and enabled only per trusted agent/provider.
- `external_action`: blocked for v2; no automatic applications, outreach, account actions, or unapproved data mutation.

Runtime safety requirements:

- CLI runtimes must never execute in a Django request/response path.
- CLI runtimes must use isolated temporary workspaces, timeout limits, output limits, and explicit environment allowlists.
- Scraped job descriptions, company pages, and uploaded files are untrusted content and cannot alter tool policy or provider permissions.
- The app must work with AI disabled; agent features should show a clear disabled/configuration state.
- Runtime results may propose changes, but only saved user approval can mutate profile, CV, application, alert, or watchlist data.

Observability:

- LangSmith is optional AI observability, not a required agent framework.
- The Django Agent Orchestrator records the local source of truth first: run, steps, artifacts, decisions, permissions, invocation metadata, and audit logs.
- When `LANGSMITH_TRACING=true` and `LANGSMITH_API_KEY` is configured, runtime calls may be traced with redacted inputs and provider/model metadata.
- Store the LangSmith trace ID in local audit metadata so users can cross-reference external traces.
- Do not adopt LangChain just to get tracing; LangSmith works without LangChain.

Durable workflow boundary:

- Current v2 uses Django-managed agent runs for bounded review tasks.
- LangGraph is not required for the first deployable release.
- Add LangGraph only if workflows need branching, long waits, replay/resume semantics, or multi-step state machines that become awkward in the Django run/step model.
- If LangGraph is added, it must run behind Django as an execution engine and must not bypass permissions, redaction, budgets, approval gates, local audit logs, or artifact storage.

Durable workflows that may justify LangGraph later:

- Company Watch Workflow: scan tracked company, classify new roles, dedupe/noise-check, match profile, then create alert or digest.
- Profile-to-Role Match Workflow: refresh profile snapshot, score jobs, explain gaps, wait for feedback, then propose strategy/filter changes.
- Application Prep Workflow: generate CV notes, cover note, recruiter message, and answer bank, then wait for approval before saving artifacts.
- Weekly Learning Workflow: summarize feedback, propose title/filter/source-health changes, wait for approval, then apply accepted changes only.

### Profile Builder Agent

Purpose: turn scattered developer career data into a strong, structured profile.

Inputs:

- Resume/CV upload or pasted text.
- GitHub profile URL.
- Portfolio URL.
- LinkedIn URL/exported profile text.
- Project READMEs.
- Existing `cv.md`, `profile.yml`, `profile.md`, and proof-point files.

Steps:

1. Parse resume into clean markdown sections.
2. Extract skills, roles, projects, education, links, and career timeline.
3. Analyze GitHub/portfolio/project data for proof points.
4. Generate `cv.md`, `profile.yml`, and `profile.md` drafts.
5. Generate target role archetypes and initial title list.
6. Flag weak, unsupported, or ambiguous claims.
7. Ask user to confirm, edit, or reject generated claims.

Outputs:

- Draft `cv.md`.
- Draft `profile.yml`.
- Draft `profile.md`.
- Skill inventory.
- Proof point library.
- Target role map.
- Profile completeness checklist.

User approval required before:

- Saving generated profile files.
- Using generated claims in CVs/applications.
- Marking inferred skills as confirmed.

### Job Discovery Agent

Purpose: continuously find better opportunities, not just more opportunities.

Inputs:

- Target roles.
- Generated job titles.
- Skill inventory.
- Location preferences.
- Company watchlist.
- Saved/ignored job feedback.

Steps:

1. Expand role titles into search keywords and synonyms.
2. Generate negative keywords from user preferences.
3. Recommend companies based on target role, stack, and saved jobs.
4. Scan ATS/company sources.
5. Deduplicate jobs and detect reposts.
6. Rank new jobs for match review.
7. Update scan history and alert candidates.

Outputs:

- New jobs.
- Similar-company suggestions.
- Search query updates.
- Source quality notes.
- Freshness and repost signals.
- Suggested alert-rule changes.

User approval required before:

- Adding many new companies to the watchlist.
- Changing major search strategy.
- Enabling noisy sources.

### Match Review Agent

Purpose: deeply evaluate promising jobs against the user profile.

Inputs:

- Job description.
- Company data.
- `cv.md`.
- `profile.yml`.
- `profile.md`.
- Proof points and skill inventory.

Steps:

1. Classify role family, seniority, domain, work mode, and location.
2. Map JD requirements to exact CV/profile evidence.
3. Calculate match, confidence, knowledge coverage, and gap scores.
4. Identify hard blockers vs nice-to-have gaps.
5. Produce apply/skip recommendation.
6. Suggest CV/profile improvements.
7. Create interview prep seed notes for strong matches.

Outputs:

- Match report.
- Evidence table.
- Gap mitigation plan.
- Apply priority.
- Resume tailoring plan.
- Interview prep seed.

User approval required before:

- Moving a job into application workflow.
- Updating CV/profile from match recommendations.

### Application Prep Agent

Purpose: prepare high-quality application material without inventing experience.

Inputs:

- Selected job.
- Match report.
- Confirmed profile and proof points.
- Existing CV versions.

Steps:

1. Generate JD-specific CV changes.
2. Reorder bullets by relevance.
3. Generate ATS keyword coverage report.
4. Draft short cover note.
5. Draft recruiter message.
6. Draft answers for common application questions.
7. Save artifacts to the application workspace.

Outputs:

- Tailored CV draft.
- Keyword coverage report.
- Cover note.
- Recruiter message.
- Application answer drafts.
- Portfolio proof point suggestions.

User approval required before:

- Exporting final CV.
- Marking materials as ready.
- Copying messages into outreach/application flow.

### Follow-Up Agent

Purpose: prevent applications from going stale.

Inputs:

- Application tracker.
- Application dates.
- Interview dates.
- User-defined follow-up cadence.

Steps:

1. Find applications needing follow-up.
2. Draft concise follow-up messages.
3. Create daily action queue items.
4. Snooze or reschedule based on user action.

Outputs:

- Follow-up tasks.
- Follow-up message drafts.
- Due dates.

User approval required before:

- Sending or copying any message externally.

### Interview Prep Agent

Purpose: turn a job and profile into focused preparation.

Inputs:

- Job description.
- Match report.
- Company research.
- Confirmed STAR story bank.
- Proof point library.

Steps:

1. Identify likely technical and behavioral topics.
2. Map requirements to STAR stories.
3. Suggest project case study to lead with.
4. Generate recruiter/hiring-manager questions.
5. Identify red flags and clarifications.
6. Create a prep checklist.

Outputs:

- Interview prep brief.
- STAR story mapping.
- Technical topic checklist.
- Questions to ask.
- Red-flag checklist.

### Search Strategy Agent

Purpose: improve the job search based on results.

Inputs:

- Scan history.
- Saved/ignored jobs.
- Application outcomes.
- Source quality analytics.
- User feedback.

Steps:

1. Review weekly search performance.
2. Identify high-signal roles, companies, and sources.
3. Identify noisy terms and weak sources.
4. Recommend company/source/title filter changes.
5. Recommend profile or project improvements that would unlock better matches.

Outputs:

- Weekly strategy review.
- Search-query changes.
- Company recommendations.
- Negative keyword recommendations.
- Profile/project improvement tasks.

User approval required before:

- Applying preference updates.
- Changing alert thresholds.
- Adding/removing sources.

### Agent Run Lifecycle

Each agent run should move through explicit states:

- Queued.
- Running.
- Needs user input.
- Completed.
- Failed.
- Cancelled.
- Applied.
- Rejected.

Every run should store:

- Agent type.
- Trigger source.
- Input snapshot.
- Step log.
- Output artifacts.
- Token/cost estimate when AI is used.
- User decisions.
- Applied changes.
- Error details.

### Agent Triggers

Agents can be triggered by:

- User action.
- New job discovered.
- Scheduled scan completed.
- Profile updated.
- Application status changed.
- Follow-up due.
- Weekly strategy review schedule.

All scheduled or automatic triggers should respect user settings and quiet hours.

## CV and Application Tools

V2 should help users create a detailed developer CV/profile and then tailor it per job.

Features:

- CV markdown editor with preview.
- Versioned CV snapshots.
- Profile completeness checklist.
- ATS-friendly CV export.
- JD-specific CV export.
- Per-job tailored summary and bullet reorder.
- Keyword coverage report.
- "Do not invent skills" guardrail.
- Claim verification: mark generated claims as confirmed, needs edit, or rejected.
- Suggested portfolio projects to emphasize.
- LinkedIn/profile improvement suggestions.
- Interview story bank generated from real proof points.
- Reusable answer bank for common application questions.

For each job:

- Top CV changes.
- Top profile/LinkedIn changes.
- Suggested short cover note.
- Suggested recruiter message.
- Interview prep notes.

## Recruiter Intelligence

Keep this ethical and public-data-only.

Allowed:

- Public recruiter names/emails shown on job pages.
- Hiring team or department names from public pages.
- Public company career/team pages.
- Public social profile links if already linked by the company or posting.

Avoid:

- Aggressive LinkedIn scraping.
- Circumventing access controls.
- Bulk personal data collection.

Output should be "contact hints", not a people database.

## Job Discovery Improvements

To help users find more relevant opportunities, add:

- ATS portal scanning for Greenhouse, Lever, Ashby, Workday, Microsoft/Eightfold.
- Company watchlist with seeded developer-friendly companies.
- Company discovery from user skills and target roles.
- Generated search queries from target titles.
- Duplicate/repost detection.
- Posting freshness and ghost-job risk indicators.
- Saved searches.
- New-job digest.
- Manual URL inbox for jobs found elsewhere.
- Browser bookmarklet or small browser extension to save any job page into the tracker.
- Import/export for companies and tracked jobs.
- "Similar companies" suggestions based on accepted/saved jobs.
- Remote-friendly company list and location-aware filters.
- Tech-stack-specific company lists, such as Python/Django, React/Next.js, AI tooling, infra, DevTools, mobile, or data.

Useful optional sources:

- Company career pages.
- Public ATS APIs.
- GitHub org pages for developer tool companies.
- Remote job boards where scraping is permitted.
- RSS feeds where available.

## Alerts

Alert only on useful changes, not every scrape.

Triggers:

- New strong-fit job.
- New job at high-priority company.
- Job that was a stretch becomes stronger after profile update.
- Job reposted or changed.
- Deadline or posting age threshold.
- Follow-up due after application.

Channels:

- Email via SMTP.
- Local dashboard notification.
- Optional MTEANE event automation service for webhook/Discord/Slack/email rules.
- Optional webhook/Discord/Slack direct integrations later if MTEANE is not used.

MTEANE integration rules:

- MTEANE is optional infrastructure, not a required core dependency.
- Job Scout emits safe event payloads; MTEANE evaluates rules and delivers notifications.
- MTEANE failures must never block scans, alerts, applications, or agent runs.
- Event payloads must not include resumes, CV/profile markdown, secrets, personal notes, or unredacted AI prompts.

## Application Tracker

Track the user's workflow after discovery:

- Saved.
- Interested.
- Applied.
- Follow-up due.
- Interviewing.
- Rejected.
- Offer.
- Archived.

Each application should link to:

- Original job.
- Match report.
- Tailored CV version.
- Notes.
- Recruiter/contact hints.
- Follow-up reminders.
- Interview prep.

## Daily Action Queue

The app should not just collect jobs. It should tell the user what to do next.

Queue items:

- Apply now: high-fit, fresh jobs.
- Review: good-fit jobs needing user judgment.
- Fix profile: strong opportunity blocked by missing CV/profile data.
- Follow up: applications needing a follow-up.
- Prepare: interviews or calls coming soon.
- Improve: suggested small project, CV edit, or profile update that unlocks more roles.

Each item should have:

- Reason.
- Estimated effort.
- Deadline or urgency.
- One-click action.
- Dismiss/snooze option.

## Feedback Learning

The app should learn from explicit user feedback.

User feedback events:

- Mark job as relevant or irrelevant.
- Mark score too high or too low.
- Mark generated title as correct, stretch, or wrong.
- Mark company as dream, okay, fallback, or avoid.
- Mark skill as strong, weak, learning, or not interested.
- Mark AI-generated claim as accurate or inaccurate.

Learning outputs:

- Updated role/title filters.
- Updated negative keywords.
- Adjusted company tiering.
- Better alert rules.
- Better match explanations.
- More accurate future title generation.

Keep this transparent. Show what changed and allow undo.

## Analytics

Add a lightweight analytics dashboard for the user's search.

Useful metrics:

- New jobs found by source.
- Strong-fit jobs by week.
- Applications submitted.
- Response rate.
- Interview conversion rate.
- Follow-ups due.
- Top matching companies.
- Most common missing skills.
- Roles producing the best opportunities.
- Sources producing noise.

The goal is not vanity metrics. The goal is to help the user adjust search strategy.

## Interview And Offer Support

Add support after the application is submitted.

Interview features:

- Company-specific interview prep.
- JD-based likely questions.
- STAR story mapping.
- Technical topic checklist.
- "Questions to ask recruiter/hiring manager".
- Red flags to clarify.

Offer features:

- Offer comparison.
- Compensation notes.
- Negotiation script drafts.
- Decision matrix against user preferences.

## Privacy, Safety, And Data Ownership

This application will handle sensitive career data, so privacy needs to be part of the product.

Requirements:

- Local-first by default.
- Bring-your-own AI key.
- Clear AI on/off setting.
- Redact sensitive data before optional AI calls where possible.
- Show exactly what data will be sent to AI before first use.
- Export all user data.
- Import from exported data.
- Delete all local user data.
- Back up user-owned files.
- Never scrape private or authenticated pages without explicit user action.
- Never generate fake claims, fake experience, or fake credentials.

## Settings And Health Checks

Add a proper settings area:

- AI provider and model settings.
- SMTP/email settings.
- Scrape schedule settings.
- Company/source settings.
- Alert thresholds.
- Data import/export.
- Backup location.
- Diagnostics page.

Diagnostics should show:

- Database status.
- Last scan status.
- Failed scraper sources.
- Email test result.
- AI provider test result.
- Scheduler status.
- App version.

## Full Application Scope

V2 is not an MVP. It should be treated as a full-fledged personal job operating system for developers.

The application should cover the complete loop:

- Build a detailed candidate profile.
- Generate realistic target roles and search strategy.
- Discover jobs continuously.
- Score and explain fit.
- Track every opportunity.
- Tailor CV/application material.
- Surface recruiter/company intelligence.
- Manage follow-ups and interview prep.
- Learn from user feedback over time.

## Product Modules

### Profile Studio

- Resume/CV import.
- Clean markdown CV generation.
- Structured profile editor.
- Detailed developer profile generator.
- Proof point and project library.
- Skill inventory with confidence levels.
- Career narrative and role framing.
- Target role generator.
- Deal-breakers and preferences.
- Profile completeness score.
- GitHub/portfolio import.
- Confirm/reject workflow for generated claims.

### Role Intelligence

- AI-generated job titles from the user's resume/profile.
- Role family and seniority classification.
- Fit, confidence, and knowledge accuracy scoring.
- Skill gap analysis.
- Role transition paths.
- Search keyword generation.
- Negative keyword generation.
- Suggested portfolio projects to improve weak role fits.

### Discovery Engine

- Company watchlist.
- Seeded developer-friendly companies.
- Company recommendations.
- Company source detection.
- Company scan health.
- Company-specific alert rules.
- ATS scanners for Greenhouse, Lever, Ashby, Workday, Microsoft/Eightfold.
- Generic career page scanner.
- Manual URL inbox.
- Browser bookmarklet or extension capture.
- Saved searches.
- Search query generator.
- Scheduled scraping.
- Duplicate and repost detection.
- Posting freshness tracking.
- Ghost-job risk indicators.

### Match Intelligence

- Deterministic matching baseline.
- Optional AI explanation layer.
- Per-job match report.
- Skill coverage score.
- Seniority fit.
- Location/work-mode fit.
- Compensation fit.
- Company/domain fit.
- Apply priority.
- Reasons to apply.
- Reasons to skip.
- Gap mitigation plan.

### Application Workspace

- Application tracker.
- Status pipeline.
- Per-job notes.
- Tailored CV plan.
- Generated ATS CV.
- Cover note draft.
- Recruiter message draft.
- Saved artifacts.
- Follow-up reminders.
- Interview prep.
- STAR story bank.
- Reusable application answer bank.
- Offer comparison.

### Agent Workspace

- Agent run dashboard.
- Agent progress view.
- Agent artifact review.
- Approval queue.
- Claim confirmation queue.
- Retry/cancel controls.
- Agent settings and permissions.
- Cost/token visibility when AI is used.

### Recruiter And Company Intelligence

- Public contact hints.
- Hiring team hints.
- Company research summary.
- Role legitimacy signals.
- Layoff/hiring-freeze context where available.
- Compensation research.
- Interview process notes.
- Red flags and caveats.

### Daily Command Center

- Prioritized action queue.
- Today view.
- Snooze/dismiss actions.
- Follow-up queue.
- Search strategy suggestions.
- Weekly search review.

### Alerts And Automation

- New strong-fit job alerts.
- High-priority company alerts.
- Follow-up reminders.
- Saved search digests.
- Repost/change alerts.
- Email notifications.
- Local dashboard notifications.
- Optional webhook/Discord/Slack integration later.
- Weekly digest and strategy review.

### Analytics And Learning

- Search funnel analytics.
- Source quality analytics.
- Missing skill analytics.
- Feedback-based ranking adjustment.
- Transparent preference updates.
- Undoable learning changes.

### Developer Experience

- One-command local setup.
- Render deploy path.
- File import/export for `cv.md`, `profile.yml`, `profile.md`, and trackers.
- SQLite for local use.
- Postgres-ready deployment.
- Clear settings screen for AI providers, SMTP, schedules, and data export.
- No required AI key for core scraping/tracking.
- Local-first data ownership.
- Backup/export/import.
- Diagnostics and health checks.

## Feature Priority

Use this priority model to avoid building gimmicks before the core loop works.

P0: Required for the product to be useful.

- Next.js frontend shell.
- Django API.
- Single-user authentication for deployed instances.
- Company watchlist as the primary workflow.
- Company URL/name add flow.
- Company source detection.
- Company scan health dashboard.
- Manual company rescan.
- Favorite-company new-role alerts.
- Company-specific title/location/work-mode filters.
- Company-source failure diagnostics.
- ATS scanners.
- Scheduled scraping.
- Job deduplication.
- Manual relevance filters and simple relevance labels.
- Application tracker.
- Daily Action Queue.
- Strong-fit-first job view.
- Fast irrelevant-job dismissal with feedback learning.
- Basic alerts.
- Data export/import.
- Basic scan/job/agent diagnostics.
- Security controls for secrets, uploads, and user-submitted URLs.

P1: High-value features after the core loop is stable.

- Profile Studio.
- Resume/CV import and markdown profile generation.
- Generated target job titles.
- Match scoring with evidence.
- AI provider settings.
- Agent Workspace.
- Profile Builder Agent.
- Job Discovery Agent.
- Match Review Agent.
- Application Prep Agent.
- Follow-Up Agent.
- JD-specific CV export.
- Reusable application answer bank.
- Feedback learning.
- Analytics dashboard.
- Recruiter/company public intelligence.
- Interview prep.
- Search Strategy Agent.
- Company recommendations from saved/favorite companies.
- Similar-company suggestions.

P2: Useful later, but not allowed to block the main product.

- Browser extension.
- Browser bookmarklet.
- Webhook/Discord/Slack alerts.
- Offer comparison.
- Compensation research automation.
- Tech-stack-specific company catalogs.
- Advanced GitHub/portfolio import.

Deprioritized or rejected gimmicks:

- Auto-apply bot: rejected. Too risky, low trust, likely spammy, and can harm users.
- Aggressive LinkedIn scraping: rejected. Legal/ethical risk and fragile.
- Fully autonomous recruiter outreach: rejected. User must approve every message.
- Heavy 3D/visual effects: rejected. This is a productivity app, not a portfolio site.
- Social/community features: rejected for v2. They do not help the single-user job-search loop.
- Complex multi-user/team workspace: deferred. Single-user local-first is the target.
- Browser extension as a core dependency: deferred. Manual URL inbox is enough first.

## Acceptance Criteria

Every major feature should have clear acceptance criteria before implementation.

Company Watchlist is acceptable when:

- User can add a company by careers/ATS URL.
- User can add a company by name and confirm the detected careers source.
- User can see source type, source health, last scan, last success, and last failure.
- User can manually rescan one company.
- User can set company-specific title, location, work-mode, and alert filters.
- User receives an alert when a favorite company posts a relevant new role.
- User can see companies that are failing, blocked, paused, or stale.

Profile Studio is acceptable when:

- A user can paste/upload a resume and get editable `cv.md`, `profile.yml`, and `profile.md` drafts.
- Generated claims are visibly marked as unconfirmed until the user approves them.
- The user can export the profile files.
- The app can run without AI by letting the user fill fields manually.

Role Intelligence is acceptable when:

- The app generates target titles with evidence, confidence, and fit buckets.
- The user can accept, reject, or edit generated titles.
- Accepted titles drive default scans and filters.
- Negative keywords are generated and editable.

Discovery Engine is acceptable when:

- Greenhouse, Lever, Ashby, Microsoft/Eightfold, and generic career pages can be scanned.
- Company-level scan health is visible.
- New roles are detected per company.
- Scan results are deduplicated.
- Scan runs show status, errors, and source quality.
- Scheduled scans can be enabled, disabled, and manually run.

Match Intelligence is acceptable when:

- Every match report shows evidence from the CV/profile.
- Every recommendation includes reasons to apply and reasons to skip.
- Unknown data is marked unknown.
- The user can correct an incorrect score.

Application Workspace is acceptable when:

- A user can move a job through the application pipeline.
- Each application can store notes, artifacts, tailored CV drafts, and follow-up dates.
- Follow-up reminders appear in the Daily Action Queue.

Agent Workspace is acceptable when:

- Every agent run has a visible status and step log.
- Outputs are reviewable before they change user data.
- Runs can be cancelled, retried, accepted, or rejected.
- Cost/token estimates are visible when AI is used.

Privacy/Data Ownership is acceptable when:

- User can export all personal data.
- User can delete all personal data.
- AI calls show what data is being sent before first use.
- The app works in no-AI mode for scraping, tracking, and manual profile management.

Security is acceptable when:

- Deployed instances require login by default.
- Secrets are never shown or logged.
- User-submitted URLs cannot access private/local network targets by default.
- File uploads have type and size validation.
- Scraped content cannot change agent/tool permissions.

Operational readiness is acceptable when:

- Failed scans are visible with reason and retry action.
- Failed agent runs are visible with reason and retry/cancel action.
- Worker and scheduler status are visible in diagnostics.
- Export/import can be tested on a fresh database.
- Logs avoid storing full resumes, secrets, or full AI prompts by default.

## Software Engineering Plan

Development should follow a controlled engineering process, not a feature rush.

1. Requirements baseline:
   - Keep this plan as the product baseline.
   - Convert P0 features into issues with acceptance criteria.
   - Record explicit non-goals and deferred features.

2. Architecture design:
   - Write an architecture decision record for Next.js + Django + workers.
   - Define API boundaries before frontend implementation.
   - Define async job lifecycle before building agents.
   - Define import/export formats before creating profile models.

3. Data design:
   - Model user-owned data separately from system-owned data.
   - Add migration plans for all new models.
   - Define deletion/export behavior for every personal-data model.
   - Add indexes for job dedupe, scan history, and match lookup.

4. Implementation:
   - Build vertical slices instead of isolated UI screens.
   - Each slice must include backend, frontend, tests, and basic docs.
   - Keep AI integrations behind service interfaces so providers can change.
   - Keep deterministic fallbacks for critical paths.

5. Testing:
   - Unit tests for parsers, scoring, dedupe, filters, and profile transforms.
   - Integration tests for API flows.
   - Worker/job tests for retries and failure states.
   - Frontend tests for critical workflows.
   - End-to-end smoke tests for onboarding, scan, match, application tracking.
   - Regression fixtures for ATS scraper adapters.

6. Quality gates:
   - Type checking for frontend.
   - Django checks and Python tests.
   - Linting/formatting.
   - Migration check.
   - Basic accessibility check for core screens.
   - Security review for AI data sharing and scraping boundaries.

7. Release:
   - Use feature flags for incomplete modules.
   - Keep data migrations reversible where reasonable.
   - Provide backup/export before major schema changes.
   - Document upgrade steps.

## SPM Planning And Control

Use software project management controls from the start.

Planning artifacts:

- Product baseline: this plan.
- Architecture decision records.
- API contract.
- Data model diagram.
- Risk register.
- Release roadmap.
- Sprint backlog.
- Test plan.
- Definition of Done.

Control metrics:

- P0 feature completion.
- Open critical bugs.
- Scraper success rate by source.
- AI failure rate.
- Agent run failure rate.
- Average scan duration.
- Duplicate detection accuracy.
- Match feedback correction rate.
- Test coverage for critical modules.
- Data export/import success.

Cadence:

- Weekly planning review.
- Weekly risk review.
- Weekly demo of working vertical slices.
- Backlog grooming before each implementation block.
- Retrospective after each major release slice.

Change control:

- New P0 scope requires explicit approval.
- P2 features cannot be pulled forward unless a P0/P1 dependency requires them.
- Any feature touching user data needs privacy review.
- Any feature sending data to AI needs user-consent review.
- Any scraper touching a new source needs legal/robots/terms review.

Definition of Done:

- Acceptance criteria met.
- Tests added or updated.
- Empty/error/loading states handled.
- User data export/delete behavior considered.
- AI fallback or no-AI behavior defined.
- Documentation updated.
- No critical known regressions.

## Risk Register

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Scope creep from too many modules | High | High | Enforce P0/P1/P2 priority and release roadmap. |
| Product becomes another noisy job aggregator | High | High | Strong-fit-first UX, anti-noise principles, daily action queue, feedback learning. |
| Product drifts away from company tracking | High | Medium | Watchlist-first IA, company tracking P0 gates, profile/AI features remain support layers. |
| Favorite-company scan health is unreliable | High | High | Source health dashboard, adapter tests, conservative scan cadence, readable failure diagnostics. |
| User misses a favorite-company role despite tracking | High | Medium | New-role detection tests, scan history, alert verification, manual rescan, stale-source warnings. |
| Users apply to more jobs but get no better outcomes | High | Medium | Optimize for application quality, tailored materials, follow-up discipline, and user outcome metrics. |
| AI invents or exaggerates candidate claims | High | Medium | Claim confirmation workflow, evidence citations, no unconfirmed claims in CVs. |
| Prompt injection from job descriptions or scraped pages | High | Medium | Treat external content as untrusted, fixed tool permissions, approval gates for data changes. |
| Auto-agent behavior harms user trust | High | Medium | No auto-apply, no auto-contact, approvals required for external actions. |
| Scrapers break due to ATS/page changes | High | High | Adapter tests, scan diagnostics, source quality reporting, graceful failures. |
| User-submitted URLs cause SSRF or internal network access | High | Medium | Validate URL schemes/hosts, block private networks, enforce timeouts and redirect limits. |
| Uploaded resumes/documents create parser/security issues | High | Medium | File type/size validation, defensive parsing, never execute uploaded content. |
| Serverless/timeouts break long workflows | High | Medium | Use Django/Python workers for long-running jobs. |
| Private data leaks to AI provider | High | Medium | Explicit AI consent, redaction, provider settings, preview payload before first use. |
| AI cost runs away on large scans | Medium | Medium | Deterministic pre-filtering, per-run/daily budgets, run expensive AI only for shortlisted jobs. |
| Matching scores feel arbitrary | Medium | High | Evidence tables, confidence buckets, user correction feedback. |
| User receives too many alerts | Medium | Medium | Alert thresholds, daily digest, quiet hours, source quality filters. |
| Repost/duplicate logic misses jobs | Medium | Medium | Normalize title/company/location/source IDs; allow manual merge/unmerge. |
| Browser extension delays core app | Medium | Medium | Defer extension to P2; manual URL inbox first. |
| Recruiter intelligence crosses ethical line | High | Low | Public-data-only rule, no aggressive LinkedIn scraping, contact hints only. |
| Deployment becomes too complex | Medium | Medium | One-command local setup, Render docs, diagnostics, optional no-worker mode for dev. |
| Data model becomes hard to migrate | Medium | Medium | ADRs, migrations per slice, export/import contract, backup before schema changes. |
| V1 users lose existing companies/jobs during migration | High | Low | Import-only migration path, original database untouched, readable import report. |
| Logs accidentally capture sensitive profile data | High | Medium | Privacy-safe structured logging, scrub secrets/resumes/prompts by default. |
| Poor information architecture makes feature-rich app hard to use | Medium | Medium | Build around Today, Jobs, Companies, Profile, Applications, Agents, Analytics, Settings. |

## Resolved Decisions And Open Questions Before Build

These items are either resolved implementation decisions or questions that must be resolved during architecture design:

- AI provider strategy is decided: use a pluggable Django Agent Orchestrator from day one, implement direct API support first, and add Gemini CLI, Claude Code CLI, OpenCode, OpenRouter, DeepSeek, and other adapters behind worker-only runtime contracts.
- Should v2 live in the same repo as Django v1 or become a monorepo with `frontend/` and `backend/`?
- Which queue should be used first: Celery + Redis, Django-Q, RQ, or a simpler management-command scheduler?
- What is the first deployment target: Render only, local-only first, or Docker-based?
- Should generated user-layer files be stored on disk, in the database, or both?
- What is the exact export/import format for user-owned data?
- Which ATS adapters are P0 for the first full release?
- How much company intelligence can be collected without web search/API dependencies?
- What authentication approach should protect deployed single-user instances?
- What are the first SLOs for scan duration, worker reliability, and UI response time?
- What data should be excluded from logs and AI payloads by default?
- What prompt/model evaluation dataset should be built before trusting match scores?
- How should v1 data be imported and verified?
- Should Docker be required for full worker/scheduler parity in local development?
- What exact outcome metrics will prove this is better than manual job-board search?
- What is the smallest dogfood experiment that can disprove the product value hypothesis?

## Release Roadmap

Phases are for execution order only. The target product is the full application above.

1. Architecture, security baseline, company data contracts, v1 migration design, and deployment topology.
2. Next.js shell, Django API, authentication, diagnostics, and import/export foundation.
3. Company Watchlist, source detection, scan health, manual rescan, and favorite-company alerts.
4. Discovery Engine and scheduled scraping.
5. Profile Studio, Role Intelligence, and company-specific filters.
6. Match Intelligence and job ranking.
7. Application Workspace and tailored CV generation.
8. Recruiter/company intelligence.
9. Daily Action Queue, alerts, and automation.
10. Agent Workspace and controlled agentic workflows.
11. Analytics, feedback learning, and search strategy review.
12. Privacy/export/import hardening, deployment hardening, diagnostics, and onboarding refinement.

The implementation waves are fully expanded in `docs/v2-build-tasks.md` under "Wave Execution Roadmap" and mirrored in `docs/v2-progress.md` under "Planned Future Waves". Agentic workflow contracts are maintained in `docs/agentic-workflows.md`. Any new feature must be inserted into that wave roadmap before implementation.

## Data Models To Add

Initial Django model candidates. Final fields and relationships must be defined during data design before implementation:

- `UserProfile`
- `CandidateDocument`
- `TrackedCompany`
- `CompanySource`
- `CompanyWatchRule`
- `CompanyScanHealth`
- `CompanyAlertPreference`
- `TargetRole`
- `GeneratedJobTitle`
- `Skill`
- `ProofPoint`
- `ProjectProofPoint`
- `ImportedProfileSource`
- `JobMatch`
- `Application`
- `ApplicationArtifact`
- `ApplicationQuestionAnswer`
- `AlertRule`
- `AlertEvent`
- `ScanRun`
- `JobChange`
- `ContactHint`
- `UserFeedbackEvent`
- `PreferenceLearningEvent`
- `DailyAction`
- `SearchStrategy`
- `CompanyTier`
- `DataExport`
- `AuditLog`
- `SystemSetting`
- `ExternalSource`
- `SavedSearch`
- `ImportRun`
- `ExportRun`
- `AgentRun`
- `AgentStep`
- `AgentArtifact`
- `AgentDecision`
- `AgentPermission`
- `AgentTrigger`

Keep single-user self-hosted mode first. Multi-user auth can come later if needed.

## Review Notes

The useful features are the ones that improve targeting, reduce noise, or create a clear next action. Features that mainly make the product feel larger without improving the job-search loop should stay out of the core roadmap.

Highest-value additions:

- Role title expansion from resume/profile.
- Skill synonym expansion.
- Negative filters.
- Company tiering.
- Freshness scoring.
- Repost detection.
- Gap-to-project suggestions.
- Feedback learning.
- Search query generation.
- Daily Action Queue.

Lowest-value or riskiest additions:

- Auto-apply.
- Aggressive recruiter scraping.
- Heavy visual effects.
- Social/community features.
- Browser extension before the core app is stable.

The product advantage should stay focused: better targeting, less noise, evidence-backed recommendations, and a clear next action for every job.
