# Job Scout v2 Progress

This file is the live implementation ledger for v2. `docs/v2-plan.md` remains the product baseline, and `docs/v2-build-tasks.md` remains the task catalog.

Rules:

- Check this file before changing owned areas.
- Update task status when starting, blocking, reviewing, or completing work.
- Record touched paths and verification commands.
- Do not mark a task done without verification or an explicit note explaining why verification was not run.

Status values:

- `not started`
- `in progress`
- `blocked`
- `review`
- `done`

## Wave 1 Status

| Task | Status | Owner | Touched paths | Verification | Blockers | Updated |
|------|--------|-------|---------------|--------------|----------|---------|
| `0.x` Repo and branch preparation | `done` | main coordinator | `Backend/`, `Frontend/`, `README.md`, `docs/` | Backend and frontend checks passed | None | 2026-05-05 |
| `1.7` Django Agent Orchestrator architecture | `done` | main coordinator | `docs/v2-plan.md`, `docs/v2-build-tasks.md` | Documentation review in final diff | None | 2026-05-05 |
| `4.x` Company watchlist backend slice | `done` | backend worker + main coordinator | `Backend/companies/`, `Backend/api/`, `Backend/dashboard/` imports | `makemigrations --check --dry-run`, `manage.py check`, `manage.py test` | None | 2026-05-05 |
| `5.x` Company watchlist frontend slice | `done` | frontend worker + main coordinator | `Frontend/src/app/`, `Frontend/src/components/`, `Frontend/src/lib/` | `npm run lint`, `npm run build`, route smoke checks | None | 2026-05-05 |

## Wave 1 Acceptance Checklist

- [x] `docs/v2-progress.md` tracks implementation status.
- [x] Django Agent Orchestrator/runtime router is part of the main v2 plan and task catalog.
- [x] Company API returns source health, priority, active/paused state, scan metadata, and failure count.
- [x] Company API supports create, list, detail, update, delete, pause, resume, and rescan.
- [x] Legacy dashboard still imports working company lifecycle/scrape services.
- [x] Next.js default landing page is replaced by an app shell.
- [x] Navigation reaches Today, Companies, Jobs, Profile, Applications, Agents, Analytics, and Settings.
- [x] `/companies` lists tracked companies when the backend is available.
- [x] `/companies` shows a clear backend-down state.
- [x] Add-company flow posts to the Django API.
- [x] Backend verification passes.
- [x] Frontend verification passes.

## Wave 2 Status

| Task | Status | Owner | Touched paths | Verification | Blockers | Updated |
|------|--------|-------|---------------|--------------|----------|---------|
| `4.5` Company-specific filters | `done` | backend/frontend workers + main coordinator | `Backend/companies/`, `Backend/api/`, `Frontend/src/app/companies/`, `Frontend/src/components/companies/`, `Frontend/src/lib/api/` | Backend tests, frontend lint/build, live route smoke checks | None | 2026-05-05 |
| `5.5` Company pause/resume/edit/delete UI | `done` | frontend worker + main coordinator | `Frontend/src/app/companies/`, `Frontend/src/components/companies/`, `Frontend/src/lib/api/` | `npm run lint`, `npm run build`, `/companies` smoke check | None | 2026-05-05 |
| `6.5` Scan diagnostics and logs | `done` | backend/frontend workers + main coordinator | `Backend/companies/`, `Backend/api/`, `Frontend/src/app/companies/`, `Frontend/src/components/companies/` | Backend tests, `/api/companies/logs`, `/companies` smoke check | None | 2026-05-05 |
| `7.x` Diagnostics, export, import foundation | `done` | backend/frontend workers + main coordinator | `Backend/api/`, `Frontend/src/app/settings/`, `Frontend/src/components/settings/`, `Frontend/src/lib/api/` | Backend tests, `/api/diagnostics`, `/api/export`, `/settings` smoke check | None | 2026-05-05 |

## Wave 2 Acceptance Checklist

- [x] Company API supports company-specific title, location, and work-mode filters.
- [x] Company UI supports edit, pause/resume, delete, and filter fields.
- [x] Company scan logs are exposed by API and visible in the Companies page.
- [x] Diagnostics endpoint reports database, agent worker, scan scheduler, LangSmith, AI config, SMTP config, and counts without leaking secrets.
- [x] Export endpoint includes app version, generated timestamp, companies, and jobs without secrets.
- [x] Company import endpoint accepts a watchlist payload and returns readable created/updated/error counts.
- [x] Settings page exposes diagnostics, export, and import controls.
- [x] Backend verification passes.
- [x] Frontend verification passes.

## Wave 3 Status

| Task | Status | Owner | Touched paths | Verification | Blockers | Updated |
|------|--------|-------|---------------|--------------|----------|---------|
| `8.1` Scan job lifecycle | `done` | main coordinator | `Backend/companies/`, `Backend/api/` | Backend tests, `/api/scans` smoke check | None | 2026-05-05 |
| `8.2` Scheduled scan command | `done` | main coordinator | `Backend/companies/management/commands/` | `manage.py scan_due_companies --dry-run --limit 3` | None | 2026-05-05 |
| `8.3` Overlap prevention | `done` | main coordinator | `Backend/companies/services.py`, `Backend/api/` | Backend overlap test | None | 2026-05-05 |
| `8.4` New-role detection | `done` | main coordinator | `Backend/companies/`, `Backend/jobs/`, `Backend/api/` | Backend alert dedupe test | None | 2026-05-05 |
| `8.5` Local alerts foundation | `done` | main coordinator | `Backend/companies/`, `Backend/api/`, `Frontend/src/app/`, `Frontend/src/lib/api/` | Backend tests, `/api/alerts` and `/` smoke checks | None | 2026-05-05 |
| `8.6` Scan cadence controls | `done` | main coordinator | `Backend/companies/`, `Frontend/src/app/companies/` | Backend tests, `/companies` smoke check | None | 2026-05-05 |
| `8.7` Quiet hours and digest settings | `done` | main coordinator | `Backend/notifications/`, `Backend/api/`, `Frontend/src/app/settings/` | Backend tests, frontend build | Completed in Wave 9 | 2026-05-05 |

## Wave 3 Acceptance Checklist

- [x] Scan jobs have explicit queued, running, success, partial success, failed, cancelled, and skipped states.
- [x] Manual scans use the scan job lifecycle and prevent overlapping scans for the same company.
- [x] A management command can run due company scans without UI interaction.
- [x] New matching jobs create local alert records.
- [x] Duplicate jobs do not create duplicate alerts.
- [x] Company scan cadence and new-role alert preferences are persisted and editable.
- [x] Today page surfaces unread alerts, recent scan jobs, and failed scan attention items.
- [x] Backend verification passes.
- [x] Frontend verification passes.
- [x] Quiet hours and digest settings are implemented in Wave 9.

## Wave 4 Status

| Task | Status | Owner | Touched paths | Verification | Blockers | Updated |
|------|--------|-------|---------------|--------------|----------|---------|
| `9.1` Application tracker models/statuses | `done` | main coordinator | `Backend/applications/`, `Backend/api/` | Backend tests, `/api/applications` smoke check | None | 2026-05-05 |
| `9.2` Daily action model | `done` | main coordinator | `Backend/applications/`, `Backend/api/` | Backend tests, `/api/today/actions` smoke check | None | 2026-05-05 |
| `9.3` New-role and follow-up actions | `done` | main coordinator | `Backend/applications/`, `Backend/api/`, `Frontend/src/app/` | Backend tests, `/` smoke check | None | 2026-05-05 |
| `9.4` Today queue UI | `done` | main coordinator | `Frontend/src/app/`, `Frontend/src/lib/api/` | `npm run lint`, `npm run build`, `/` smoke check | None | 2026-05-05 |
| `9.5` Application pipeline UI | `done` | main coordinator | `Frontend/src/app/applications/`, `Frontend/src/lib/api/` | `npm run lint`, `npm run build`, `/applications` smoke check | None | 2026-05-05 |

## Wave 4 Acceptance Checklist

- [x] New unread role alerts become Today review actions.
- [x] User can save or skip a role from Today.
- [x] User can update application status, notes, next action, and follow-up date.
- [x] Follow-up applications appear in Today when due.
- [x] Applications page shows a basic pipeline grouped by status.
- [x] Backend verification passes.
- [x] Frontend verification passes.

## Wave 5 Status

| Task | Status | Owner | Touched paths | Verification | Blockers | Updated |
|------|--------|-------|---------------|--------------|----------|---------|
| `10.1` Manual profile fields | `done` | main coordinator | `Backend/profiles/`, `Backend/api/`, `Frontend/src/app/profile/` | Backend tests, `/api/profile`, `/profile` smoke check | None | 2026-05-05 |
| `10.2` Resume/CV markdown import | `done` | main coordinator | `Backend/profiles/`, `Backend/api/`, `Frontend/src/app/profile/` | Backend tests, `/api/profile/import-resume` smoke check | None | 2026-05-05 |
| `10.3` Generated target titles | `done` | main coordinator | `Backend/profiles/`, `Backend/api/`, `Frontend/src/app/profile/` | Backend tests, `/api/profile` smoke check | None | 2026-05-05 |
| `10.4` Claim confirmation workflow | `done` | main coordinator | `Backend/profiles/`, `Backend/api/`, `Frontend/src/app/profile/` | Backend tests, frontend lint/build | None | 2026-05-05 |
| `10.5` Accepted titles improve company filters | `done` | main coordinator | `Backend/profiles/`, `Backend/companies/`, `Backend/api/`, `Frontend/src/app/profile/` | Backend tests, frontend lint/build | None | 2026-05-05 |

## Wave 5 Acceptance Checklist

- [x] Profile setup remains optional and company tracking still works without a profile.
- [x] User can edit manual profile fields.
- [x] User can paste resume/CV text and get editable markdown CV/profile output.
- [x] Target titles include fit bucket, confidence, knowledge accuracy, and evidence.
- [x] Generated claims are unconfirmed until explicitly confirmed.
- [x] User can accept/reject target titles and confirm/reject claims.
- [x] Accepted target titles can be applied to company title filters.
- [x] Backend verification passes.
- [x] Frontend verification passes.

## Wave 6 Status

| Task | Status | Owner | Touched paths | Verification | Blockers | Updated |
|------|--------|-------|---------------|--------------|----------|---------|
| `11.1` Django Agent Orchestrator/runtime router | `done` | main coordinator | `Backend/agents/`, `Backend/api/`, `Frontend/src/app/agents/` | Backend tests, `/api/agents/runs` smoke check | None | 2026-05-05 |
| `11.2` Agent run/step/artifact/decision/permission/runtime models | `done` | main coordinator | `Backend/agents/` | `makemigrations --check --dry-run`, backend tests | None | 2026-05-05 |
| `11.3` Provider settings | `done` | main coordinator | `Backend/agents/`, `Backend/api/`, `Frontend/src/app/agents/` | `/api/agents/providers`, frontend build | None | 2026-05-05 |
| `11.4` Runtime adapter interface | `done` | main coordinator | `Backend/agents/runtime.py` | Backend tests | None | 2026-05-05 |
| `11.5` Direct API/local deterministic adapter foundation | `done` | main coordinator | `Backend/agents/` | `/api/agents/runs` Profile Builder smoke check | None | 2026-05-05 |
| `11.7` Tool policy, audit logs, cancellation, retry | `done` | main coordinator | `Backend/agents/`, `Backend/api/` | Backend tests | None | 2026-05-05 |
| `11.8` Run lifecycle APIs | `done` | main coordinator | `Backend/api/`, `Frontend/src/lib/api/` | Backend tests, `/api/agents/runs?limit=1` smoke check | None | 2026-05-05 |
| `11.9` Agent dashboard | `done` | main coordinator | `Frontend/src/app/agents/` | `npm run lint`, `npm run build`, `/agents` smoke check | None | 2026-05-05 |
| `11.10` Profile Builder Agent foundation | `done` | main coordinator | `Backend/agents/`, `Frontend/src/app/agents/` | Backend tests, frontend build | None | 2026-05-05 |

## Wave 6 Acceptance Checklist

- [x] Agent runs store input snapshot, provider/model, tool policy, status, steps, artifacts, permissions, runtime invocations, and audit logs.
- [x] Provider settings exist for direct API, OpenRouter, DeepSeek, Gemini CLI, Claude Code CLI, and OpenCode without storing secrets.
- [x] Agent run lifecycle APIs support list/detail/start/cancel/retry.
- [x] Tool policy levels are explicit and external action remains blocked.
- [x] Profile Builder Agent can produce a reviewable artifact without mutating profile data.
- [x] UI shows disabled/no-AI states, provider/model metadata, run history, steps, artifacts, retry, and cancel.
- [x] CLI runtimes are represented as worker-only disabled adapters and do not run in a web request.
- [x] Backend verification passes.
- [x] Frontend verification passes.

## Wave 7 Status

| Task | Status | Owner | Touched paths | Verification | Blockers | Updated |
|------|--------|-------|---------------|--------------|----------|---------|
| `12.1` Source quality metrics | `done` | main coordinator | `Backend/analytics/`, `Backend/api/`, `Frontend/src/app/analytics/` | Backend tests, `/api/analytics` smoke check | None | 2026-05-05 |
| `12.2` Alert usefulness tracking | `done` | main coordinator | `Backend/analytics/`, `Backend/api/`, `Frontend/src/app/analytics/` | Backend tests | None | 2026-05-05 |
| `12.3` Ignored/relevant feedback capture | `done` | main coordinator | `Backend/analytics/`, `Backend/api/`, `Frontend/src/app/analytics/` | Backend tests, frontend build | None | 2026-05-05 |
| `12.4` Noisy company/source/keyword surfacing | `done` | main coordinator | `Backend/analytics/`, `Frontend/src/app/analytics/` | Backend tests, `/analytics` smoke check | None | 2026-05-05 |
| `12.5` Transparent filter improvement suggestions | `done` | main coordinator | `Backend/analytics/`, `Frontend/src/app/analytics/` | Backend tests, frontend build | None | 2026-05-05 |

## Wave 7 Acceptance Checklist

- [x] Analytics API reports source quality by company and platform from scan, alert, application, and feedback data.
- [x] User can mark alert usefulness as relevant, maybe, or irrelevant without mutating jobs/applications.
- [x] Feedback is persisted with reason/tags and is included in export without secrets.
- [x] Analytics page surfaces useful, noisy, failing, and stale tracking signals.
- [x] Filter suggestions explain the evidence and require user review before any company filters change.
- [x] Backend verification passes.
- [x] Frontend verification passes.

## Wave 8 Status

| Task | Status | Owner | Touched paths | Verification | Blockers | Updated |
|------|--------|-------|---------------|--------------|----------|---------|
| `13.1` Render deployment for Backend/Frontend split | `done` | main coordinator | `render.yaml`, `Backend/build.sh`, `README.md`, `docs/` | Frontend build, smoke script | None | 2026-05-05 |
| `13.2` Environment templates | `done` | main coordinator | `Backend/.env.example`, `Frontend/.env.example` | File review | None | 2026-05-05 |
| `13.3` Deployment diagnostics docs | `done` | main coordinator | `docs/deployment.md` | File review | None | 2026-05-05 |
| `13.4` Backup/export instructions | `done` | main coordinator | `docs/backup-export.md` | File review | None | 2026-05-05 |
| `13.5` Smoke-test checklist | `done` | main coordinator | `scripts/smoke-test.sh`, `docs/smoke-test.md` | `./scripts/smoke-test.sh` | None | 2026-05-05 |

## Wave 8 Acceptance Checklist

- [x] Root Render Blueprint defines separate Backend and Frontend services.
- [x] Backend migrations run as a deploy step, not during build.
- [x] Env templates document required and optional variables without secrets.
- [x] Backup/export guidance explains app JSON export and database backup expectations.
- [x] Smoke-test script/checklist covers health, company add, scan endpoint, alerts, export, and frontend load.
- [x] Backend verification passes.
- [x] Frontend verification passes.

## Wave 9 Status

| Task | Status | Owner | Touched paths | Verification | Blockers | Updated |
|------|--------|-------|---------------|--------------|----------|---------|
| `8.7` Quiet hours and digest settings | `done` | main coordinator | `Backend/notifications/`, `Backend/api/`, `Frontend/src/app/settings/`, `Frontend/src/components/settings/` | Backend tests, frontend build, `/api/notifications/preferences`, `/settings` smoke checks | None | 2026-05-05 |

## Wave 9 Acceptance Checklist

- [x] User can view and update notification preferences from Settings.
- [x] Quiet hours include enabled flag, start, end, and timezone.
- [x] Digest settings include enabled flag, cadence, delivery time, and channel.
- [x] Preferences are included in diagnostics/export without secrets.
- [x] Backend verification passes.
- [x] Frontend verification passes.

## Wave 10 Status

| Task | Status | Owner | Touched paths | Verification | Blockers | Updated |
|------|--------|-------|---------------|--------------|----------|---------|
| Match data model | `done` | main coordinator | `Backend/matching/`, `Backend/api/` | `makemigrations --check --dry-run`, backend tests | None | 2026-05-05 |
| Deterministic match scoring | `done` | main coordinator | `Backend/matching/` | Backend tests, `/api/jobs` smoke check | None | 2026-05-05 |
| Jobs API match serialization | `done` | main coordinator | `Backend/api/`, `Frontend/src/lib/api/` | Backend tests, `/api/export` smoke check | None | 2026-05-05 |
| Strong-fit-first Jobs page | `done` | main coordinator | `Frontend/src/app/jobs/` | `npm run lint`, `npm run build`, `/jobs` smoke check | None | 2026-05-05 |

## Wave 10 Acceptance Checklist

- [x] Jobs API includes deterministic match report with score, confidence, apply priority, evidence, reasons, and gaps.
- [x] Match scoring uses profile target titles, skills, location/work-mode preferences, seniority terms, and job text.
- [x] Jobs page ranks strong fits first and shows evidence without AI-generated claims.
- [x] Match reports are persisted and included in export without secrets.
- [x] Profile remains optional; jobs still load when no profile exists.
- [x] Backend verification passes.
- [x] Frontend verification passes.

## Planned Future Waves

These waves cover the remaining full-application scope from `docs/v2-plan.md`. Do not add new feature work outside this roadmap unless the plan is updated with an explicit wave, task group, owner, write scope, and acceptance criteria.

| Wave | Status | Scope | Task group | Primary paths | Dependency |
|------|--------|-------|------------|---------------|------------|
| 11 | `done` | Authentication and deployed-instance security | `15.x` | `Backend/accounts/`, `Backend/api/`, `Backend/jobhunt/`, `Frontend/src/app/`, `docs/security.md` | Wave 8 |
| 12 | `done` | Profile Studio completion and profile file export/import | `16.x` | `Backend/profiles/`, `Backend/api/`, `Frontend/src/app/profile/`, `docs/` | Wave 5 |
| 13 | `done` | Role Intelligence and search strategy controls | `17.x` | `Backend/profiles/`, `Backend/matching/`, `Backend/analytics/`, `Frontend/src/app/profile/`, `Frontend/src/app/analytics/` | Waves 5, 10, 12 |
| 14 | `done` | Discovery expansion and scraper coverage | `18.x` | `Backend/scrapers_engine/`, `Backend/companies/`, `Backend/jobs/`, `Frontend/src/app/companies/`, `Frontend/src/app/jobs/` | Waves 1-3 |
| 15 | `done` | Application artifacts, CV tailoring, answer bank | `19.x` | `Backend/applications/`, `Backend/api/`, `Frontend/src/app/applications/`, `Frontend/src/app/jobs/` | Waves 4, 10, 12 |
| 16 | `done` | AI runtime consent, budgets, durable workers, CLI adapters | `20.x` | `Backend/agents/`, worker config, `Backend/api/`, `Frontend/src/app/agents/`, `Frontend/src/app/settings/`, `docs/ai-runtime.md` | Waves 6, 8, 11 |
| 17 | `done` | Match Review, Application Prep, Follow-Up, Search Strategy agents | `21.x` | `Backend/agents/`, `Backend/matching/`, `Backend/applications/`, `Frontend/src/app/agents/`, `Frontend/src/app/jobs/`, `Frontend/src/app/applications/` | Waves 10, 15, 16 |
| 18 | `done` | Recruiter and company intelligence | `22.x` | `Backend/intelligence/`, `Backend/api/`, `Frontend/src/app/companies/`, `Frontend/src/app/applications/` | Waves 10, 15 |
| 19 | `done` | Interview prep and offer support | `23.x` | `Backend/applications/`, `Backend/interviews/`, `Frontend/src/app/applications/` | Waves 15, 18 |
| 20 | `done` | Analytics learning and weekly search review | `24.x` | `Backend/analytics/`, `Backend/matching/`, `Backend/agents/`, `Frontend/src/app/analytics/`, `Frontend/src/app/` | Waves 7, 10, 13 |
| 21 | `done` | Data ownership, full restore, delete, redaction | `25.x` | `Backend/api/`, `Backend/*/`, `Frontend/src/app/settings/`, `docs/` | All personal-data modules |
| 22 | `done` | Quality, accessibility, CI, release gates | `26.x` | `Backend/`, `Frontend/`, `docs/`, CI config | All P0/P1 modules |
| 23 | `done` | Optional P2 integrations | `27.x` | Integration-specific paths only | Stable core product |
| 24 | `done` | Full release stabilization and dogfood validation | `28.x` | Whole repository, docs, tests, release notes | Waves 1-23 |

## Wave 11-15 Implementation Ledger

| Wave | Status | Touched paths | Verification | Blockers | Updated |
|------|--------|---------------|--------------|----------|---------|
| 11 Auth/security baseline | `done` | `Backend/api/auth.py`, `Backend/jobhunt/settings.py`, `Backend/companies/services.py`, `Frontend/src/lib/api/client.ts`, `Backend/.env.example`, `Frontend/.env.example`, `docs/security.md` | Focused API auth/URL safety tests, full backend tests, frontend lint/build, live API smoke | None | 2026-05-05 |
| 12 Profile Studio completion | `done` | `Backend/profiles/`, `Backend/api/`, `Frontend/src/app/profile/`, `Frontend/src/lib/api/` | Focused profile tests, migration check, full backend tests, frontend lint/build | None | 2026-05-05 |
| 13 Role/search strategy controls | `done` | `Backend/profiles/`, `Backend/api/`, `Frontend/src/app/profile/`, `Frontend/src/lib/api/` | Focused search strategy generate/apply test, full backend tests, frontend lint/build | None | 2026-05-05 |
| 14 Discovery expansion baseline | `done` | `Backend/discovery/`, `Backend/api/`, `Backend/jobhunt/settings.py`, `Frontend/src/app/jobs/`, `Frontend/src/lib/api/` | Focused manual inbox tests, full backend tests, frontend lint/build, live `/api/discovery/inbox` smoke | None | 2026-05-05 |
| 15 Application artifacts/tailoring | `done` | `Backend/applications/`, `Backend/api/`, `Frontend/src/app/applications/`, `Frontend/src/lib/api/` | Focused artifact generation/review test, full backend tests, frontend lint/build, live `/api/applications` smoke | None | 2026-05-05 |

## Wave 16-20 Implementation Ledger

| Wave | Status | Touched paths | Verification | Blockers | Updated |
|------|--------|---------------|--------------|----------|---------|
| 16 AI runtime consent/budgets/workers | `done` | `Backend/agents/`, `Backend/api/`, `Backend/jobhunt/settings.py`, `Backend/.env.example`, `Frontend/src/app/agents/`, `Frontend/src/lib/api/`, `docs/ai-runtime.md` | Focused runtime tests, `process_agent_queue`, full backend tests, frontend lint/build, live `/api/agents/runtime` smoke | None | 2026-05-05 |
| 17 Agent workflows | `done` | `Backend/agents/`, `Backend/matching/`, `Backend/applications/`, `Frontend/src/app/agents/`, `Frontend/src/lib/api/` | Focused workflow agent test, full backend tests, frontend lint/build | None | 2026-05-05 |
| 18 Company/recruiter intelligence | `done` | `Backend/intelligence/`, `Backend/api/`, `Backend/jobhunt/settings.py`, `Frontend/src/app/companies/`, `Frontend/src/components/companies/`, `Frontend/src/lib/api/` | Focused company intelligence/contact test, full backend tests, frontend lint/build, live `/api/companies` smoke | None | 2026-05-05 |
| 19 Interview prep/offer support | `done` | `Backend/interviews/`, `Backend/api/`, `Backend/jobhunt/settings.py`, `Frontend/src/app/applications/`, `Frontend/src/lib/api/` | Focused interview/offer test, full backend tests, frontend lint/build, live `/api/applications` smoke | None | 2026-05-05 |
| 20 Weekly analytics review | `done` | `Backend/analytics/`, `Backend/api/`, `Frontend/src/app/analytics/`, `Frontend/src/lib/api/` | Focused weekly review test, full backend tests, frontend lint/build, live `/api/analytics` smoke | None | 2026-05-05 |

## Task Group 21-28 Completion Ledger

This ledger uses the task-group numbers from `docs/v2-build-tasks.md`. Groups `21.x`-`24.x` were previously implemented in waves 17-20 and received gap-closure in this pass.

| Task group | Status | Scope | Touched paths | Verification | Blockers | Updated |
|------------|--------|-------|---------------|--------------|----------|---------|
| `21.x` | `done` | Agent workflows after matching, approval queue, safe accept/reject | `Backend/agents/`, `Backend/api/`, `Frontend/src/app/agents/`, `Frontend/src/lib/api/` | Focused agent decision test, full backend tests, frontend lint/build | None | 2026-05-05 |
| `22.x` | `done` | Recruiter and company intelligence richness/public-source policy | `Backend/intelligence/`, `Backend/api/`, `Frontend/src/lib/api/` | Focused company intelligence test, full backend tests | None | 2026-05-05 |
| `23.x` | `done` | Interview checklist/stage and manual-first offer support fields | `Backend/interviews/`, `Backend/api/`, `Frontend/src/lib/api/` | Focused interview/offer test, full backend tests | None | 2026-05-05 |
| `24.x` | `done` | Match corrections, undoable learning changes, weekly analytics review | `Backend/analytics/`, `Backend/matching/`, `Backend/api/`, `Frontend/src/lib/api/` | Focused match correction/undo test, full backend tests | None | 2026-05-05 |
| `25.x` | `done` | Full workspace restore, delete-all-personal-data, redaction audit, docs | `Backend/api/data_ownership.py`, `Backend/api/`, `Frontend/src/app/settings/`, `Frontend/src/components/settings/`, `docs/data-ownership.md`, `docs/migration-safety.md` | Focused restore/delete/redaction tests, full backend tests, frontend build, smoke script | None | 2026-05-05 |
| `26.x` | `done` | Backend regressions, frontend interaction/a11y contracts, CI and release gates | `Backend/api/tests.py`, `Frontend/scripts/`, `Frontend/package.json`, `.github/workflows/quality.yml`, `scripts/smoke-test.sh`, `docs/quality-release.md` | `manage.py test`, `npm run lint`, `npm run test:interactions`, `npm run test:a11y`, `npm run build`, smoke script | Smoke app-create step skipped because local DB had no stored jobs | 2026-05-05 |
| `27.x` | `done` | Optional P2 integration artifacts and policy | `scripts/job-scout-bookmarklet.js`, `docs/optional-integrations.md` | File review, frontend/backend gates | None | 2026-05-05 |
| `28.x` | `done` | Release audit, deferrals, dogfood plan, release notes | `docs/v2-release-audit.md`, `docs/release-notes-v2.md`, `docs/v2-progress.md` | Full verification suite and smoke script | Dogfood execution remains a real-world follow-up, not a local automated test | 2026-05-05 |

## Remaining Scope Control

- P0 remaining: none from the current v2 plan.
- P1 remaining: deeper scraper/source coverage if manual inbox data shows repeated gaps, richer external intelligence imports, agent execution workers beyond deterministic local adapters.
- P2 remaining: browser extension, webhook/Slack/Discord, advanced GitHub/portfolio import, compensation automation beyond manual-first notes, richer tech-stack catalogs.
- Rejected remains rejected: auto-apply bot, aggressive LinkedIn scraping, fully autonomous outreach, social/community features, heavy visual effects, complex multi-user workspace.
- Any new idea must be classified as P0/P1/P2/rejected and inserted into a new wave before implementation.

## Deployment Readiness Waves

These waves move v2 from feature-complete planning toward a deployable personal app. They are tracked separately from product scope because they should not introduce new core features.

| Wave | Status | Scope | Touched paths | Verification | Blockers | Updated |
|------|--------|-------|---------------|--------------|----------|---------|
| 29 | `in progress` | Stabilize current v2, scraper false-positive fix, dogfood report | `Backend/scrapers_engine/`, `docs/` | Generic nav false-positive tests, baseline dogfood report, and full backend tests pass | One-week real dogfood still required | 2026-05-05 |
| 30 | `review` | Docker/VPS backend stack | `Backend/Dockerfile`, `docker-compose.yml`, `docs/vps-docker.md` | YAML parse passed; MTEANE worker now waits on healthy API/migrations; Docker unavailable in this environment | Needs `docker compose config` and local/VPS boot check on a machine with Docker | 2026-05-05 |
| 31 | `done` | Vercel frontend deployment docs and smoke auth | `docs/vercel.md`, `Frontend/.env.example`, `scripts/smoke-test.sh` | `bash -n scripts/smoke-test.sh`, `npm run lint`, `npm run build` | None | 2026-05-05 |
| 32 | `done` | Optional MTEANE service and event publisher | `.gitmodules`, `integrations/mteane`, `Backend/notifications/`, `docs/mteane.md` | Submodule initialized; backend tests pass | Runtime MTEANE smoke requires Docker/API key setup | 2026-05-05 |
| 33 | `in progress` | Release operations, real dogfood, export/restore validation, staging/commit | `Backend/api/`, `Backend/jobhunt/settings.py`, `docker-compose.yml`, `docs/`, git index | Export/restore now carries full application records, export no longer refreshes job matches, scanner diagnostics use backend-visible configuration; focused restore/diagnostics/export tests and full backend tests pass | Requires one-week dogfood, Docker boot check, and logical staging/commit | 2026-05-05 |
| 34 | `planned` | Durable agentic workflows and LangGraph boundary | `Backend/agents/`, workflow modules, `Frontend/src/app/agents/`, `docs/ai-runtime.md` | LangSmith optional tracing implemented; LangGraph boundary documented | Workflow implementation after deploy foundation and dogfood signal | 2026-05-05 |
