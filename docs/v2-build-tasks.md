# Job Scout v2 Build Tasks

This file turns the v2 product plan into implementation workstreams that can be picked up by separate agents or engineers.

The core product is company tracking first: users should not miss roles posted by favorite companies. Profile, AI, matching, and application tooling support that loop; they should not block the company-watchlist foundation.

## Delivery Rules

- Build vertical slices, not isolated UI-only or backend-only islands.
- Keep `Backend/` and `Frontend/` ownership separate when possible.
- Every task group must define acceptance criteria before implementation.
- P0 tasks must land before P1/P2 work unless a P1 task is strictly required by a P0 task.
- No agent should modify another agent's owned files without checking the latest status first.
- No auto-apply, auto-outreach, or unconfirmed AI-generated claims.
- Every async workflow needs visible status, retry/cancel behavior, and readable failure messages.

## Target Repository Shape

```text
Company-Data-scraper/
  Backend/
    manage.py
    requirements.txt
    jobhunt/
    companies/
    jobs/
    dashboard/          # legacy v1 UI can remain temporarily
    api/
    scrapers_engine/
    templates/
    static/
    docs/
  Frontend/
    package.json
    next.config.*
    src/
  docs/
    v2-plan.md
    v2-build-tasks.md
```

## Task Dependency Map

Can run early:

- `0.x` branch/repo preparation
- `1.x` architecture contracts
- `2.x` backend move and compatibility
- `3.x` frontend scaffold

Can run in parallel after `1.x`:

- `4.x` company watchlist backend
- `5.x` frontend app shell
- `6.x` scraper/source health improvements
- `7.x` import/export and diagnostics

Can run after watchlist and source health basics:

- `8.x` scheduled scans and alerts
- `9.x` application tracker
- `10.x` profile/role intelligence

Later:

- `11.x` agent workspace
- `12.x` analytics and feedback learning
- `13.x` deployment hardening
- `14.x` authentication and deployed-instance security
- `15.x` profile studio completion
- `16.x` role intelligence and search strategy
- `17.x` discovery expansion
- `18.x` application workspace artifacts and tailoring
- `19.x` AI runtime, consent, and worker execution
- `20.x` agent workflows after matching
- `21.x` recruiter and company intelligence
- `22.x` interview and offer support
- `23.x` analytics learning and weekly review
- `24.x` data ownership hardening
- `25.x` data ownership and restore hardening
- `26.x` quality, accessibility, and release gates
- `27.x` optional P2 integrations
- `28.x` full release stabilization

## Wave Execution Roadmap

This roadmap maps the product plan into implementation waves. Completed waves remain listed so future agents can see what is already done; planned waves define every remaining product area from `docs/v2-plan.md`.

| Wave | Status | Primary Scope | Task Groups | Dependency |
|------|--------|---------------|-------------|------------|
| 1 | done | Repo split, app shell, company watchlist vertical slice | `0.x`, `1.7`, `4.x`, `5.x` | None |
| 2 | done | Company filters, diagnostics, import/export foundation | `4.5`, `5.5`, `6.5`, `7.x` | Wave 1 |
| 3 | done | Scheduled scans, scan jobs, alerts | `8.1`-`8.6` | Wave 2 |
| 4 | done | Today queue and application tracker | `9.x` | Wave 3 |
| 5 | done | Profile and target-title foundation | `10.x` | Wave 4 |
| 6 | done | Agent workspace foundation | `11.1`-`11.5`, `11.7`-`11.10` | Wave 5 |
| 7 | done | Analytics and feedback foundation | `12.x` | Waves 3-6 |
| 8 | done | Deployment hardening | `13.x` | Repo split |
| 9 | done | Quiet hours and digest preferences | `8.7` | Wave 3 |
| 10 | done | Deterministic match intelligence and Jobs page | `14.x` in this file | Waves 5, 7 |
| 11 | done | Authentication and deployed-instance security | `15.x` | Wave 8 |
| 12 | done | Profile Studio completion and profile file exports | `16.x` | Wave 5 |
| 13 | done | Role Intelligence and search strategy controls | `17.x` | Waves 5, 10, 12 |
| 14 | done | Discovery expansion and scraper coverage | `18.x` | Waves 1-3 |
| 15 | done | Application Workspace artifacts and tailoring | `19.x` | Waves 4, 10, 12 |
| 16 | done | AI runtime consent, budgets, and worker execution | `20.x` | Waves 6, 8, 11 |
| 17 | done | Match Review, Application Prep, and Follow-Up agents | `21.x` | Waves 10, 15, 16 |
| 18 | done | Recruiter and company intelligence | `22.x` | Waves 10, 15 |
| 19 | done | Interview prep and offer support | `23.x` | Waves 15, 18 |
| 20 | done | Analytics learning and weekly search review | `24.x` | Waves 7, 10, 13 |
| 21 | done | Data ownership hardening and full restore/delete | `25.x` | All personal-data modules |
| 22 | done | Quality gates, accessibility, e2e, release readiness | `26.x` | All P0/P1 modules |
| 23 | done | Optional P2 integrations | `27.x` | Stable core product |
| 24 | done | Final full-release stabilization | `28.x` | Waves 1-23 |
| 29 | in progress | Stabilize current v2 and dogfood findings | `29.x` | Wave 24 |
| 30 | review | Docker/VPS deployment stack | `30.x` | Wave 29 |
| 31 | done | Vercel frontend deployment path | `31.x` | Wave 30 |
| 32 | done | Optional MTEANE event automation service | `32.x` | Wave 30 |
| 33 | planned | Release operations and real dogfood validation | `33.x` | Waves 29-32 |

## Product Scope Coverage Matrix

| Product Plan Area | Covered By Waves | Notes |
|-------------------|------------------|-------|
| Repo/developer experience | 1, 8, 22, 24, 30, 31, 33 | Includes split repo, local setup, Render deployment, Docker/VPS path, smoke tests, CI/release gates. |
| Company Watchlist | 1, 2, 3, 14, 29, 33 | Core watchlist is done; source quality still requires real dogfood. |
| Discovery Engine | 3, 7, 13, 14, 20 | Scheduled scans, manual URL inbox, and analytics are done; deeper source coverage remains P1 only if dogfood exposes gaps. |
| Profile Studio | 5, 12 | Manual profile/resume import, proof points, `profile.yml`, downloads, and completeness are implemented. |
| Role Intelligence | 5, 10, 13 | Target titles, deterministic matching, strategy controls, and transition paths are implemented. |
| Match Intelligence | 10, 17, 20 | Deterministic baseline, correction learning, and Match Review Agent are implemented. |
| Application Workspace | 4, 15, 17, 19 | Tracker, artifacts, tailoring, agents, and interview prep are implemented. |
| Agent Workspace | 6, 16, 17, 34 | Control plane, durable queue mode, consent, local agents, optional LangSmith tracing, and LangGraph boundary are planned/implemented; real external adapters remain P1. |
| Recruiter/Company Intelligence | 18 | Public-source-only intelligence is implemented and bounded. |
| Daily Command Center | 4, 9, 20 | Today queue and weekly search review are implemented. |
| Alerts and automation | 3, 9, 23 | Basic/local alerts and preferences are done; optional webhooks/Slack/Discord remain P2. |
| Analytics and learning | 7, 20 | Source/feedback analytics, ranking correction, and weekly review are implemented. |
| Privacy/data ownership | 2, 8, 21, 22, 33 | Export, full redacted restore, delete-all, and redaction audit are implemented; real-data restore validation remains a release gate. |
| Security | 11, 16, 21, 22, 33 | Auth, URL safety, AI consent, log redaction, deploy auth checks, and security QA are implemented. |
| Interview/offer support | 19 | Interview prep and offer support are implemented. |
| Optional P2 integrations | 23 | Browser capture, webhooks, advanced imports, compensation automation are opt-in later work. |
| Rejected/deferred boundaries | 24 | Auto-apply, aggressive scraping, autonomous outreach, social features, and multi-user workspace stay out of v2 unless explicitly reapproved. |

## 0.x Repo And Branch Preparation

Owner: main coordinator.

Write scope:

- Git branch state.
- Top-level folder moves.
- `README.md`.
- Root docs.

Tasks:

- `0.1` Switch to `v2`.
- `0.2` Fast-forward local `main` from `origin/main`.
- `0.3` Fast-forward/merge `main` into `v2`.
- `0.4` Preserve v2 planning docs on `v2`.
- `0.5` Create `Frontend/`.
- `0.6` Move current Django project into `Backend/`.
- `0.7` Update root README with v2 repo layout and startup notes.

Acceptance:

- `git status --short --branch` shows `v2`.
- `Backend/manage.py` exists.
- `Frontend/package.json` exists after scaffold.
- Root docs remain available.
- No existing v1 code is deleted accidentally.

## 1.x Architecture Contracts

Owner: architecture agent.

Write scope:

- `docs/architecture/`
- `docs/api-contract.md`
- `docs/data-contract.md`
- `docs/adr/`

Tasks:

- `1.1` Write ADR for Next.js + Django + Python workers.
- `1.2` Define API boundary between Frontend and Backend.
- `1.3` Define async job lifecycle contract.
- `1.4` Define user-owned data import/export contract.
- `1.5` Define source health states and company scan states.
- `1.6` Define security baseline for auth, secrets, URLs, uploads, and AI payloads.
- `1.7` Define Django Agent Orchestrator ADR: runtime router, provider settings, adapter contract, tool policy levels, audit logging, artifact storage, and disabled/no-AI behavior.

Acceptance:

- Contracts are specific enough for frontend/backend agents to build against.
- Async states include queued, running, partial success, failed, cancelled, retrying.
- Export/import includes company watchlist data and user-owned profile data.
- Agent orchestration contract makes Django the control plane and keeps CLI/API runtimes behind worker-only adapters.

## 2.x Backend Restructure

Owner: backend infrastructure agent.

Write scope:

- `Backend/`
- Root scripts only if needed for delegation from root.

Tasks:

- `2.1` Move Django files into `Backend/`.
- `2.2` Update paths in scripts, settings, docs, and package references.
- `2.3` Keep v1 Django app runnable from `Backend/`.
- `2.4` Add root convenience scripts if useful.
- `2.5` Run Django tests after the move.

Acceptance:

- `cd Backend && python manage.py check` passes.
- `cd Backend && python manage.py test` passes.
- Existing scraper behavior still works.
- Static/build commands are either updated or documented as legacy.

## 3.x Frontend Scaffold

Owner: frontend infrastructure agent.

Write scope:

- `Frontend/`

Tasks:

- `3.1` Create Next.js app in `Frontend/`.
- `3.2` Use TypeScript.
- `3.3` Add app shell with routes for Today, Jobs, Companies, Profile, Applications, Agents, Analytics, Settings.
- `3.4` Add API client wrapper for Backend.
- `3.5` Add base design tokens for a clean productivity UI.
- `3.6` Add empty/loading/error state components.

Acceptance:

- `cd Frontend && npm run build` passes.
- App has placeholder routes without broken navigation.
- Frontend API base URL is configurable.

## 4.x Company Watchlist Backend

Owner: backend domain agent.

Write scope:

- `Backend/companies/`
- `Backend/api/`
- `Backend/jobs/` only for company relation changes.

Tasks:

- `4.1` Add company watchlist models: tracked company, source, watch rules, alert preferences, scan health.
- `4.2` Add company priority tiers: dream, high, normal, fallback, paused.
- `4.3` Add source health states: active, needs setup, degraded, failing, paused, blocked.
- `4.4` Add APIs for list/create/update/delete/pause/rescan companies.
- `4.5` Add company-specific title/location/work-mode filters.
- `4.6` Add tests for watchlist and health state transitions.

Acceptance:

- User can add company by URL through API.
- User can pause/resume a company.
- API returns source health and last scan metadata.
- Tests cover active, failing, paused, and blocked states.

## 5.x Company Watchlist Frontend

Owner: frontend product agent.

Write scope:

- `Frontend/src/app/companies/`
- Shared frontend components.

Tasks:

- `5.1` Build company list page.
- `5.2` Build add-company flow.
- `5.3` Show source health and last scan status.
- `5.4` Add manual rescan button.
- `5.5` Add pause/resume/edit/delete.
- `5.6` Add company-specific filters UI.

Acceptance:

- User can manage tracked companies from UI.
- Failing/degraded/blocked sources are visually clear.
- Manual rescan action shows queued/running/success/failure state.

## 6.x Scraper And Source Health

Owner: scraping agent.

Write scope:

- `Backend/scrapers_engine/`
- `Backend/companies/`
- `Backend/jobs/`

Tasks:

- `6.1` Normalize scraper result format.
- `6.2` Add source detection helpers.
- `6.3` Improve Greenhouse, Lever, Ashby, Microsoft/Eightfold adapters.
- `6.4` Add generic careers fallback with clear limitations.
- `6.5` Add scan health reporting.
- `6.6` Add duplicate/repost detection.
- `6.7` Add source fixture tests.

Acceptance:

- Scraper failures do not crash whole scans.
- Each scan records success/failure and readable reason.
- Duplicate jobs are detected across repeated scans.
- Fixture tests cover supported ATS adapters.

## 7.x Diagnostics, Import, Export

Owner: backend platform agent.

Write scope:

- `Backend/api/`
- `Backend/settings` or equivalent app if created.
- `docs/`

Tasks:

- `7.1` Add diagnostics endpoint for database, agent worker, scan scheduler, AI config, SMTP config.
- `7.2` Add export for companies/jobs/user profile data.
- `7.3` Add import for company watchlist.
- `7.4` Add v1 import design or command.
- `7.5` Ensure secrets are never included in export.

Acceptance:

- Export can be imported into a fresh database.
- Diagnostics never reveal secret values.
- Failed imports produce readable reports.

## 8.x Scheduled Scans And Alerts

Owner: automation agent.

Write scope:

- `Backend/companies/`
- `Backend/jobs/`
- `Backend/notifications/` if created.
- Worker/scheduler config.

Tasks:

- `8.1` Define scan job model/lifecycle.
- `8.2` Add scheduled scan command or worker task.
- `8.3` Prevent overlapping scans per company/source.
- `8.4` Add new-role detection.
- `8.5` Add basic email/local alerts.
- `8.6` Add scan cadence and per-company alert preferences.
- `8.7` Add quiet hours and digest settings.

Acceptance:

- User can trigger a manual scan.
- Scheduled scan can run without UI interaction.
- New relevant roles create alert records.
- Alerts are not sent for duplicates.

## 9.x Today Queue And Application Tracker

Owner: workflow agent.

Write scope:

- `Backend/applications/` if created.
- `Backend/api/`
- `Frontend/src/app/today/`
- `Frontend/src/app/applications/`

Tasks:

- `9.1` Add application tracker models/statuses.
- `9.2` Add daily action model.
- `9.3` Create actions for new favorite-company roles and follow-ups.
- `9.4` Build Today queue UI.
- `9.5` Build basic application pipeline UI.

Acceptance:

- New relevant role can become a Today action.
- User can save/apply/skip a role.
- User can set follow-up date.
- Follow-up appears in Today queue.

## 10.x Profile And Role Intelligence

Owner: profile/AI agent.

Write scope:

- `Backend/profile/` if created.
- `Backend/matching/` if created.
- `Frontend/src/app/profile/`

Tasks:

- `10.1` Add manual profile fields.
- `10.2` Add resume/CV import and markdown generation.
- `10.3` Add generated target titles.
- `10.4` Add claim confirmation workflow.
- `10.5` Use accepted titles to improve company alert filters.

Acceptance:

- Profile setup is optional, not blocking company tracking.
- Generated claims are not treated as confirmed.
- Accepted titles can update alert filters.

## 11.x Agent Workspace

Owner: agent workflow agent.

Write scope:

- `Backend/agents/` if created.
- `Frontend/src/app/agents/`
- Runtime adapter configuration/docs only when owned by the agent workflow slice.

Tasks:

- `11.1` Add Django Agent Orchestrator/runtime router as the backend control plane.
- `11.2` Add agent run/step/artifact/decision/permission/runtime invocation models.
- `11.3` Add provider settings for direct API, OpenRouter/DeepSeek, Gemini CLI, Claude Code CLI, and OpenCode.
- `11.4` Add runtime adapter interface with prepare, execute, collect artifacts, and failure summarization methods.
- `11.5` Implement direct API adapter first for structured low-risk tasks.
- `11.6` Implement worker-only CLI adapter wrapper for Gemini CLI, Claude Code CLI, and OpenCode after the direct API adapter works.
- `11.7` Add tool policy enforcement, audit logs, cancellation, retry, approval gates, and safe rerun behavior.
- `11.8` Add run lifecycle APIs.
- `11.9` Build agent run dashboard with steps, logs, artifacts, provider/model metadata, approvals, retry, cancel, and disabled/no-AI states.
- `11.10` Implement Profile Builder Agent first.
- `11.11` Implement Match Review Agent after matching data exists.

Acceptance:

- Agent runs are reviewable, cancellable, retryable.
- No agent changes user data without approval.
- Agent output stores prompt/model version when AI is used.
- User can configure provider/model per agent type.
- Direct API runtime works without shell access.
- CLI runtimes never run inside a web request and only run in isolated worker workspaces.
- Every runtime call stores input snapshot, provider/model, tool policy, output/artifacts, errors, and user-safe failure reason.
- Prompt injection from scraped jobs cannot alter tool permissions.

## 12.x Analytics And Feedback Learning

Owner: analytics agent.

Write scope:

- `Backend/analytics/` if created.
- `Frontend/src/app/analytics/`

Tasks:

- `12.1` Track source quality metrics.
- `12.2` Track alert usefulness.
- `12.3` Track ignored/relevant feedback.
- `12.4` Surface noisy companies/sources/keywords.
- `12.5` Suggest filter improvements.

Acceptance:

- User can see which company sources are useful/noisy.
- User can see missed/late/failing tracking signals.
- Feedback can change future filters transparently.

## 13.x Deployment And Hardening

Owner: release agent.

Write scope:

- Deployment config.
- `docs/`
- Root scripts.

Tasks:

- `13.1` Update Render deployment for Backend/Frontend split.
- `13.2` Add env templates.
- `13.3` Add deployment diagnostics docs.
- `13.4` Add backup/export instructions.
- `13.5` Add smoke-test checklist.

Acceptance:

- Fresh setup instructions work.
- Render deployment path is documented.
- Smoke tests cover company add, scan, alert, export.

## 14.x Match Intelligence And Job Ranking

Owner: matching agent.

Write scope:

- `Backend/matching/`
- `Backend/api/`
- `Frontend/src/app/jobs/`
- `Frontend/src/lib/api/`

Tasks:

- `14.1` Add persisted match report model.
- `14.2` Add deterministic match scoring baseline.
- `14.3` Score title, skills, seniority, location/work mode, confidence, and knowledge coverage.
- `14.4` Add evidence, reasons to apply, reasons to skip, gaps, and apply priority.
- `14.5` Serialize match reports through jobs API and export.
- `14.6` Build strong-fit-first Jobs page.
- `14.7` Keep profile optional and mark unknown/low-confidence data clearly.

Acceptance:

- Jobs API includes match report data for every job.
- Jobs page ranks strong fits first.
- Every score has deterministic evidence.
- No AI claims are used for baseline matching.
- Match reports export without secrets.

## 15.x Authentication And Security Baseline

Owner: security agent.

Write scope:

- `Backend/accounts/` or Django auth configuration.
- `Backend/api/`
- `Backend/jobhunt/`
- `Frontend/src/app/`
- `docs/security.md`

Tasks:

- `15.1` Add single-user authentication for deployed instances.
- `15.2` Add setup flow for first admin/user credential.
- `15.3` Protect API endpoints by default outside local development.
- `15.4` Add CSRF/session or token strategy for the Next.js frontend.
- `15.5` Add URL safety checks for user-submitted company/careers URLs.
- `15.6` Block private/local-network fetch targets by default.
- `15.7` Add security docs for secrets, auth, URL validation, and AI data sharing.

Acceptance:

- Deployed instance requires login by default.
- Local development can still run without painful setup.
- Secrets are never returned by diagnostics/export.
- User-submitted URLs cannot access private network targets.
- Tests cover protected endpoints and URL validation.

## 16.x Profile Studio Completion

Owner: profile agent.

Write scope:

- `Backend/profiles/`
- `Backend/api/`
- `Frontend/src/app/profile/`
- Export/import docs.

Tasks:

- `16.1` Add `profile.yml` structured export alongside `cv.md` and `profile.md`.
- `16.2` Add proof point/project library.
- `16.3` Add skill inventory with confidence/evidence levels.
- `16.4` Add career timeline and role-framing fields.
- `16.5` Add profile completeness score.
- `16.6` Add profile file download/export controls.
- `16.7` Add profile import from files with validation.

Acceptance:

- User can export `cv.md`, `profile.md`, and `profile.yml`.
- Profile completeness score explains missing fields.
- Proof points and skills can be confirmed, edited, and reused.
- Profile setup remains optional for company tracking.

## 17.x Role Intelligence And Search Strategy

Owner: role intelligence agent.

Write scope:

- `Backend/profiles/`
- `Backend/matching/`
- `Backend/analytics/`
- `Frontend/src/app/profile/`
- `Frontend/src/app/analytics/`

Tasks:

- `17.1` Add role family and seniority classification to target titles.
- `17.2` Add editable search keywords and negative keywords.
- `17.3` Generate search strategy from accepted titles and feedback.
- `17.4` Add role transition path suggestions.
- `17.5` Add suggested portfolio/project gaps for weak role fits.
- `17.6` Let user apply search strategy changes to company filters after review.

Acceptance:

- Accepted titles drive positive keywords.
- Rejected/irrelevant feedback can suggest negative keywords.
- Every suggested strategy change shows evidence and requires approval.
- Role strategy improves matching/alerts without silently mutating user data.

## 18.x Discovery Expansion

Owner: discovery/scraping agent.

Write scope:

- `Backend/scrapers_engine/`
- `Backend/companies/`
- `Backend/jobs/`
- `Frontend/src/app/companies/`
- `Frontend/src/app/jobs/`

Tasks:

- `18.1` Add Workday scanner or documented fallback.
- `18.2` Improve Microsoft/Eightfold coverage with fixtures.
- `18.3` Add manual URL inbox for jobs and companies.
- `18.4` Add saved searches and generated search queries.
- `18.5` Add company recommendations and similar-company suggestions.
- `18.6` Add repost/change detection and posting freshness indicators.
- `18.7` Add ghost-job risk indicators with conservative evidence.
- `18.8` Add scraper fixture tests for every supported source.

Acceptance:

- User can capture a manual role URL without browser extension dependency.
- Scraper support and limitations are visible per source.
- Reposts/changed jobs are distinguishable from new jobs.
- Recommendations are explainable and can be dismissed.

## 19.x Application Workspace Artifacts And Tailoring

Owner: application workspace agent.

Write scope:

- `Backend/applications/`
- `Backend/api/`
- `Frontend/src/app/applications/`
- `Frontend/src/app/jobs/`

Tasks:

- `19.1` Add application artifact model.
- `19.2` Add tailored CV plan per application.
- `19.3` Add generated/editable ATS CV markdown draft.
- `19.4` Add cover note draft.
- `19.5` Add recruiter message draft.
- `19.6` Add reusable application answer bank.
- `19.7` Add artifact export/download controls.
- `19.8` Add approval workflow before any generated material is treated as final.

Acceptance:

- Application can store notes, artifacts, drafts, and follow-up dates.
- Generated drafts are visibly draft/unapproved until user approves.
- CV tailoring cites job/profile evidence.
- Artifacts export with user data.

## 20.x AI Runtime Consent, Budgets, And Worker Execution

Owner: AI platform agent.

Write scope:

- `Backend/agents/`
- Worker/runtime config.
- `Backend/api/`
- `Frontend/src/app/agents/`
- `Frontend/src/app/settings/`
- `docs/ai-runtime.md`

Tasks:

- `20.1` Add AI consent gate and preview of data sent to provider.
- `20.2` Add per-provider and per-run budget/cost fields.
- `20.3` Add token/cost accounting when provider returns usage.
- `20.4` Add durable worker execution path for long agent runs.
- `20.5` Implement direct API adapter for review-only AI tasks.
- `20.6` Implement worker-only CLI adapter wrappers for Gemini CLI, Claude Code CLI, and OpenCode.
- `20.7` Add run cancellation/retry behavior for worker-executed jobs.
- `20.8` Add prompt injection tests for scraped content and tool permissions.

Acceptance:

- AI is off until user configures and consents.
- User can see what data will be sent before first AI use.
- CLI runtimes never execute in web request handlers.
- Agent runs expose status, cost/token usage when available, artifacts, and errors.

## 21.x Agent Workflows After Matching

Owner: agent workflow agent.

Write scope:

- `Backend/agents/`
- `Backend/matching/`
- `Backend/applications/`
- `Frontend/src/app/agents/`
- `Frontend/src/app/jobs/`
- `Frontend/src/app/applications/`

Tasks:

- `21.1` Implement Match Review Agent.
- `21.2` Implement Application Prep Agent.
- `21.3` Implement Follow-Up Agent.
- `21.4` Implement Search Strategy Agent.
- `21.5` Add approval queue for proposed profile/filter/application changes.
- `21.6` Add artifact review UI by agent type.
- `21.7` Add safe accept/reject flow for every agent proposal.

Acceptance:

- Agents never auto-apply, auto-contact, or silently mutate data.
- Match Review Agent produces evidence-backed review artifacts.
- Application Prep drafts remain editable and unapproved.
- Follow-Up Agent only creates reviewable Today actions.

## 22.x Recruiter And Company Intelligence

Owner: research/intelligence agent.

Write scope:

- `Backend/intelligence/` if created.
- `Backend/api/`
- `Frontend/src/app/companies/`
- `Frontend/src/app/applications/`

Tasks:

- `22.1` Add public company research notes.
- `22.2` Add role legitimacy and caveat fields.
- `22.3` Add hiring-team/contact hints with public-source-only policy.
- `22.4` Add interview process notes.
- `22.5` Add company red flags and user notes.
- `22.6` Add recruiter/company intelligence export.

Acceptance:

- Intelligence is clearly source-labeled and editable.
- No aggressive LinkedIn scraping or private data collection.
- User can attach company/recruiter notes to applications.
- Unverified research is marked as such.

## 23.x Interview And Offer Support

Owner: interview/offer agent.

Write scope:

- `Backend/applications/`
- `Backend/interviews/` if created.
- `Frontend/src/app/applications/`

Tasks:

- `23.1` Add interview stage/checklist model.
- `23.2` Add STAR story bank.
- `23.3` Generate interview prep seeds from job/profile evidence.
- `23.4` Add recruiter/hiring-manager question list.
- `23.5` Add offer comparison fields.
- `23.6` Add compensation notes and manual research fields.

Acceptance:

- Interview prep is attached to an application.
- Prep items cite job/profile evidence where generated.
- Offer comparison is manual-first and does not require external research.

## 24.x Analytics Learning And Weekly Search Review

Owner: analytics/search strategy agent.

Write scope:

- `Backend/analytics/`
- `Backend/matching/`
- `Backend/agents/`
- `Frontend/src/app/analytics/`
- `Frontend/src/app/`

Tasks:

- `24.1` Add feedback-based ranking adjustment model.
- `24.2` Add user correction for match score too high/too low.
- `24.3` Add weekly search review report.
- `24.4` Add search funnel metrics from alert to application outcome.
- `24.5` Add missing skill analytics.
- `24.6` Add undoable preference/filter learning changes.

Acceptance:

- User corrections affect future ranking transparently.
- Weekly review explains source quality, role quality, and actions.
- Learning changes are reviewable and undoable.

## 25.x Data Ownership And Restore Hardening

Owner: data ownership agent.

Write scope:

- `Backend/api/`
- `Backend/*/`
- `Frontend/src/app/settings/`
- `docs/`

Tasks:

- `25.1` Add full import for the complete export format.
- `25.2` Add delete-all-personal-data flow.
- `25.3` Add per-domain export/delete behavior docs.
- `25.4` Add backup-before-migration reminders for risky schema changes.
- `25.5` Add restore tests on a fresh database.
- `25.6` Add log redaction audit for resumes, prompts, secrets, and scraped private data.

Acceptance:

- Export can be imported into a fresh database.
- User can delete personal data deliberately.
- Restore flow is tested and documented.
- Logs avoid storing sensitive profile/AI payloads by default.

## 26.x Quality, Accessibility, And Release Gates

Owner: QA/release agent.

Write scope:

- Tests across `Backend/` and `Frontend/`.
- `docs/`
- CI/deployment config.

Tasks:

- `26.1` Add backend regression suites for parsers, matching, dedupe, filters, and profile transforms.
- `26.2` Add frontend interaction tests for Today, Companies, Jobs, Profile, Applications, Agents, Analytics, Settings.
- `26.3` Add end-to-end smoke test for onboarding, scan, match, application tracking, export.
- `26.4` Add accessibility checks for core screens.
- `26.5` Add CI quality gate commands.
- `26.6` Add release checklist and rollback checklist.

Acceptance:

- Critical user flows are covered by automated tests or scripted smoke tests.
- Core screens meet basic accessibility standards.
- Release cannot proceed with failing backend/frontend checks.

## 27.x Optional P2 Integrations

Owner: integrations agent.

Write scope:

- Integration-specific apps/docs only.
- No core workflow rewrites.

Tasks:

- `27.1` Add browser bookmarklet after manual URL inbox is stable.
- `27.2` Evaluate browser extension only if bookmarklet is insufficient.
- `27.3` Add webhook/Discord/Slack notifications after email/local notifications are reliable.
- `27.4` Add advanced GitHub/portfolio import.
- `27.5` Add compensation research automation with strict source labeling.
- `27.6` Add tech-stack-specific company catalogs.

Acceptance:

- Optional integrations do not block core local-first workflow.
- Every external integration is opt-in.
- Every integration has privacy/security review.

## 28.x Full Release Stabilization

Owner: main coordinator.

Write scope:

- Whole repository, docs, tests, release notes.

Tasks:

- `28.1` Audit every acceptance criterion in `docs/v2-plan.md`.
- `28.2` Close or explicitly defer every planned wave item.
- `28.3` Run complete verification suite.
- `28.4` Dogfood with 25-50 tracked companies and one real developer profile.
- `28.5` Compare value against manual job-board search.
- `28.6` Prepare release notes and known limitations.

Acceptance:

- No unplanned feature remains in the v2 product plan.
- Deferred work is explicitly marked P2 or rejected.
- Dogfood results support continuing the product.

## 29.x Current V2 Stabilization

Owner: release/stabilization agent.

Write scope:

- `Backend/scrapers_engine/`
- `docs/`
- Tests related to source quality and dogfood findings.

Tasks:

- `29.1` Verify the generic career-page false-positive filter.
- `29.2` Add fixtures/tests for nav-like career links such as Home, Teams, English, and Job Search.
- `29.3` Document the initial local dogfood scan results and bad-ingestion cleanup decision.
- `29.4` Freeze core feature additions until deployment smoke passes.

Acceptance:

- Generic scraper tests reject obvious navigation links.
- Dogfood findings are documented before broader testing.
- Existing bad local dogfood data is backed up before cleanup or reset.

## 30.x Docker And VPS Deployment

Owner: deployment agent.

Write scope:

- `Backend/Dockerfile`
- Root Docker Compose files.
- Deployment docs.

Tasks:

- `30.1` Add a production-ready Django Dockerfile.
- `30.2` Add Compose services for Django web, Postgres, scheduled scanner, and agent worker.
- `30.3` Ensure local Postgres works without SSL while managed Postgres still defaults to SSL.
- `30.4` Document VPS reverse proxy, env vars, backups, update, and rollback.

Acceptance:

- `docker compose config` succeeds.
- Backend health is reachable from the Compose stack.
- Scanner and worker run as restartable separate services.

## 31.x Vercel Frontend Deployment

Owner: frontend/deployment agent.

Write scope:

- `Frontend/.env.example`
- `docs/vercel.md`
- Smoke-test scripts/docs.

Tasks:

- `31.1` Document Vercel root, install, build, and runtime envs.
- `31.2` Support smoke tests against auth-protected deployed backends.
- `31.3` Confirm frontend build still passes with server-side backend URL configuration.

Acceptance:

- Vercel docs are sufficient to deploy `Frontend/`.
- `BACKEND_API_TOKEN` remains server-side only.
- Smoke script works with deployed API-token auth.

## 32.x Optional MTEANE Service

Owner: integrations agent.

Write scope:

- `integrations/mteane`
- Optional Compose profile.
- `Backend/notifications/`
- MTEANE docs.

Tasks:

- `32.1` Link MTEANE as a git submodule.
- `32.2` Add optional Compose services for MTEANE API, worker, Postgres, and Redis.
- `32.3` Add a fail-open Django event publisher.
- `32.4` Emit safe events for new roles and scan health changes.
- `32.5` Expose MTEANE configuration status in diagnostics.

Acceptance:

- Job Scout boots when MTEANE is disabled or absent.
- MTEANE failures never fail scans, alerts, or application workflows.
- Event payloads exclude resumes, CV/profile markdown, secrets, and personal notes.

## 33.x Release Operations And Real Dogfood

Owner: main coordinator.

Write scope:

- Docs, git index, release checklist, and dogfood report.

Tasks:

- `33.1` Run complete backend/frontend/Docker/smoke verification.
- `33.2` Run at least one week of dogfood with 25-50 real companies and one real developer profile.
- `33.3` Review source health, missed roles, noisy alerts, match accuracy, and export/restore reliability.
- `33.4` Stage and commit v2 work in logical groups after gates pass.
- `33.5` Keep P1/P2 backlog explicit: hosted AI execution, deeper source coverage, browser extension, Slack/Discord/webhooks, GitHub/portfolio import, compensation automation, and tech-stack catalogs.

Acceptance:

- Dogfood produces real signal-quality conclusions.
- Export/restore is verified on real data.
- The repo is staged/committed in reviewable groups.

## 34.x Durable Agentic Workflows And LangGraph Boundary

Owner: AI platform agent.

Write scope:

- `Backend/agents/`
- `Backend/companies/`
- `Backend/matching/`
- `Backend/applications/`
- `Backend/analytics/`
- `Frontend/src/app/agents/`
- `docs/ai-runtime.md`

Tasks:

- `34.1` Keep LangSmith as optional observability for Django-owned agent runs; do not require LangChain.
- `34.2` Define workflow contracts for Company Watch, Profile-to-Role Match, Application Prep, and Weekly Learning.
- `34.3` Add explicit approval checkpoints for any workflow that mutates profile, filters, applications, artifacts, or alerts.
- `34.4` Define LangGraph adoption criteria: branching, long waits, replay/resume, or state machines that exceed the Django run/step model.
- `34.5` If LangGraph is adopted, wrap it behind the Django Agent Orchestrator as an execution engine only.
- `34.6` Preserve local audit logs, redaction, budgets, tool policy, artifacts, and user-facing result shape regardless of runtime engine.
- `34.7` Add workflow-level tests for interruption, retry, approval, prompt-injection resistance, and redacted tracing.

Acceptance:

- The first release can ship without LangGraph.
- Product-value workflows are planned and bounded.
- LangGraph has clear entry criteria and cannot bypass the Django control plane.
- LangSmith traces can be correlated to local `AgentRun` audit logs when enabled.
