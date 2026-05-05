# Job Scout V2 Frontend UI Report

This README documents the current frontend product surface for Job Scout V2. It is intended as a designer handoff and as a prompt-style source of truth for redesign work.

Job Scout is a developer-centric personal job tracking application. The core value is not "search every job board again." The product helps a user track favorite companies, monitor their career pages, understand source health, review new-role alerts, save relevant roles into an application pipeline, and gradually improve match quality from their own profile and feedback.

The frontend is a Next.js App Router application. Most screens are server-rendered and use server actions to call the Django backend. The UI is currently functional and dense, with light styling, cards, tables, forms, status badges, and metric cards. It is usable, but many workflows would benefit from a more deliberate interaction model.

## Product Mental Model

The app should feel like a personal operating console for a developer's job search:

- "Companies" are the main source objects. Users track companies they care about.
- "Scans" check company career sources for jobs.
- "Alerts" tell the user about newly discovered roles.
- "Today" is the daily triage surface.
- "Jobs" is the role review surface with match scoring and evidence.
- "Applications" is the pipeline once a role becomes actionable.
- "Profile" is the user's reusable job-search context.
- "Agents" is the AI orchestration and audit surface.
- "Analytics" tells the user whether the system is producing useful signal or noise.
- "Settings" covers diagnostics, import/export, notification preferences, and destructive data actions.

The most important product loop is:

1. User adds companies they care about.
2. System scans company career sources.
3. User reviews new-role alerts in Today.
4. User saves promising alerts as applications or skips irrelevant roles.
5. User tracks application status, follow-ups, notes, generated prep artifacts.
6. User labels alert usefulness in Analytics so future filters improve.
7. User keeps profile and search strategy updated.

## Technical Shape

- Framework: Next.js App Router.
- Styling: Tailwind CSS utility classes in components.
- Backend API base URL: `BACKEND_API_BASE_URL`, defaulting to `http://127.0.0.1:8000/api`.
- Optional backend auth token: `BACKEND_API_TOKEN`.
- Shared API wrapper: `src/lib/api/client.ts`.
- API domain functions and types: `src/lib/api/companies.ts`, `src/lib/api/types.ts`.
- Shared shell: `src/components/shell/app-shell.tsx`.
- Shared UI primitives: `MetricCard`, `PageHeader`, `StatusBadge`, `ErrorState`, `EmptyState`.

The frontend mostly avoids browser-side API calls. Server components fetch data, server actions mutate data, then pages redirect with query-string notices/errors.

## Global Shell

File: `src/components/shell/app-shell.tsx`

The app shell has a fixed information architecture:

- Desktop: left sidebar, 240px wide, hidden on small screens.
- Mobile: top header with horizontal scroll nav.
- Primary navigation:
  - Today
  - Companies
  - Jobs
  - Applications
  - Agents
  - Analytics
- Workspace navigation:
  - Profile
  - Settings

Each route uses an active `NavLink`. Desktop links show shortcut hints like `T`, `C`, `J`, `A`, `G`, `N`, but there is no keyboard shortcut behavior implemented yet.

Current shell behavior:

- Consistent layout across all pages.
- Main content is constrained to `max-w-[1480px]`.
- Mobile navigation is horizontally scrollable.
- No breadcrumbs.
- No global search.
- No global command menu.
- No persistent right rail.
- No user/account menu.

Designer notes:

- This product should stay utilitarian and work-focused. Avoid marketing-style hero sections.
- The shell should support high-frequency scanning/review workflows, not just page navigation.
- Consider adding a global command/search button for "Add company", "Paste URL", "Run scan", "Export", and "Open latest alerts".
- Consider a persistent global health indicator because backend/worker health is central to trust.
- Mobile nav needs a better compact pattern if route count grows.

## Shared UI Primitives

### PageHeader

File: `src/components/ui/page-header.tsx`

Used on every route. It displays:

- Small eyebrow label.
- Main page title.
- Short page description.
- Optional action area on the right.

Design issue:

- It works for dashboard pages, but each page's action area is inconsistent. Some pages show a status badge, some show a form, some show a link.

Recommendation:

- Standardize page-level action patterns:
  - Primary action button.
  - Secondary action menu.
  - Status indicator area.
  - Optional contextual filters below, not in the header.

### MetricCard

File: `src/components/ui/metric-card.tsx`

Displays a label, large value, and optional detail. Used heavily for summaries.

Design issue:

- Useful, but many cards are simple counts without trend/context.

Recommendation:

- Add trend, stale state, warning state, or click-through behavior where meaningful.

### StatusBadge

File: `src/components/ui/status-badge.tsx`

Used for health, status, priority, source quality, provider state, job fit, and more.

Tones:

- Neutral
- Success
- Warning
- Danger
- Info

Design issue:

- The same visual component represents many different semantic categories.

Recommendation:

- Define badge taxonomy:
  - Health badges
  - Workflow status badges
  - Priority badges
  - Source/platform badges
  - AI consent/provider badges

### ErrorState and EmptyState

Files:

- `src/components/ui/error-state.tsx`
- `src/components/ui/empty-state.tsx`

Used for backend-down states, unavailable APIs, empty companies/jobs/actions, and failed page loads.

Design issue:

- Error states are clear but not always actionable.

Recommendation:

- Add context-specific recovery actions:
  - "Open Settings"
  - "Retry"
  - "Check backend URL"
  - "Start backend command"

## Route: Today

Path: `/`

File: `src/app/page.tsx`

Purpose:

The daily command center. This is where a user should start each session. It combines backend health, company status, open actions, unread alerts, and recent scan failures.

What the user sees:

- Page header: "Today", command center description.
- Backend online/down badge.
- Success notice or error notice from recent actions.
- Backend API unavailable error if company data fails to load.
- Four metric cards:
  - Tracked companies
  - Open actions
  - Unread alerts
  - Recent failures
- Scan control panel:
  - Numeric input for scan limit.
  - "Run due scans" button.
  - Links/counts for companies to review, ready for first scan, scheduler command.
- Today actions panel:
  - Review new-role actions.
  - Follow-up actions.
  - Application next-step actions.
- Unread alerts panel:
  - New role alert cards.
  - Actions for read, dismiss, save, skip.
- Recent scans panel:
  - Recent scan jobs.
  - Source/platform status.
  - Jobs found/created/updated.

Actions available:

- Run due scans with a limit.
- Save a role alert as an application.
- Skip a role alert.
- Mark an alert read.
- Dismiss an alert.
- Complete a Today action.
- Dismiss a Today action.
- Open role URLs in a new tab.
- Navigate to Companies or Settings through attention links.

Current UX strengths:

- The page collects the right daily objects.
- The daily loop is visible: scan, review, act.
- Backend-down state is explicit.

Current UX problems:

- Today actions contain inline forms with many controls inside list rows.
- Saving an alert requires typing next action and follow-up date inline; this can feel cramped.
- Alert triage should be faster and more deliberate.
- There is no keyboard-friendly triage mode.
- There is no "review one at a time" focused flow.

Designer recommendations:

- Make Today the primary inbox.
- Use a three-zone layout:
  - Top: system health and key counts.
  - Middle: triage queue.
  - Right drawer or side panel: selected alert/action details.
- Replace dense inline forms with a slide-over detail drawer:
  - Alert details.
  - Match evidence.
  - Save as application fields.
  - Skip reason.
  - Open role.
- Add fast triage buttons:
  - Save
  - Skip
  - Later
  - Open role
- Consider keyboard shortcuts for alert triage.
- Show "why this matters today" for each action.

## Route: Companies

Path: `/companies`

Files:

- `src/app/companies/page.tsx`
- `src/components/companies/add-company-form.tsx`
- `src/components/companies/company-health-summary.tsx`
- `src/components/companies/company-list.tsx`
- `src/components/companies/recent-company-logs.tsx`

Purpose:

The watchlist and source management surface. This is the main P0 product screen because the original problem is missing when favorite companies post roles.

What the user sees:

- Page header: "Companies".
- Backend online/down badge.
- Notices for company added, updated, paused, resumed, deleted, intelligence generated.
- Scan result notice with jobs found, created, updated.
- Error state with backend API URL when company actions fail.
- Add company form:
  - Company name, optional.
  - Careers URL, required.
  - Priority: dream, high, normal, fallback.
  - Add button.
- Source health summary:
  - Tracked.
  - Active.
  - Monitoring.
  - Needs work.
- Recent scan logs:
  - Log table, or fallback logs from company metadata.
- Tracked companies table:
  - Company name and careers URL.
  - Source health.
  - Priority.
  - Active/paused state.
  - Last scan time.
  - Metadata and scan message.
  - Intelligence summary and risk count.
  - Recruiter contact count.
  - Controls.

Actions available:

- Add a company.
- Edit company and filters inside a `<details>` disclosure:
  - Name.
  - Priority tier.
  - Work mode filter.
  - Title keywords.
  - Negative title keywords.
  - Location keywords.
  - Scan frequency hours.
  - New-role alerts on/off.
- Save company changes.
- Run scan for a single company.
- Generate company intelligence.
- Pause or resume a company.
- Delete company after typing `DELETE`.
- Open careers URL.

Current UX strengths:

- The page contains all important source controls.
- It exposes source health and scan metadata clearly.
- It handles backend-down state.
- It supports detailed per-company filters.

Current UX problems:

- The company table is very wide and requires horizontal scrolling.
- Edit controls are hidden inside a native disclosure within a table cell.
- Dangerous delete action is inline with operational actions.
- Scan, Intel, Pause, Delete are all visually similar.
- Source health, scan metadata, filters, and intelligence are mixed together in one row.
- The page is information-heavy and hard to scan once the user tracks 25-50 companies.

Designer recommendations:

- Use a master-detail layout:
  - Left/main: sortable company table or list.
  - Right drawer: selected company detail.
- Keep table rows compact:
  - Company.
  - Priority.
  - Health.
  - Last scan.
  - New roles count.
  - Next scan.
  - Quick actions.
- Move edit filters into a side drawer or modal.
- Move delete into a dangerous-actions section inside the drawer.
- Add row grouping/filtering:
  - Needs attention.
  - Dream companies.
  - Unscanned.
  - Failing.
  - Paused.
- Add bulk actions:
  - Run selected scans.
  - Pause selected.
  - Apply profile filters.
- Add a visible "last found new role" or "new roles since last review" indicator.
- Consider a company health board view for source operations, but keep table as default for dense workflows.

## Route: Jobs

Path: `/jobs`

File: `src/app/jobs/page.tsx`

Purpose:

Role review and match intelligence. This page shows discovered jobs sorted strong-fit-first and explains why a role may or may not be relevant.

What the user sees:

- Page header: "Jobs".
- "Deterministic" status badge.
- Notices and errors for job/discovery actions.
- Backend unavailable state.
- Discovery inbox unavailable state.
- Four metric cards:
  - Jobs.
  - Apply now.
  - Consider.
  - Low confidence.
- Filter panel:
  - Search text.
  - Work mode.
  - Priority.
  - Reset.
  - Filter.
- Manual URL inbox:
  - Add URL form.
  - Type: auto, company, job.
  - Title.
  - Notes.
  - Pending URL list with Import and Dismiss.
- Strong-fit-first role list:
  - Role title link.
  - Company, location, remote policy.
  - Apply priority badge.
  - Scores:
    - Match.
    - Title.
    - Skills.
    - Location.
    - Confidence.
  - Evidence chips.
  - Reasons to apply.
  - Reasons to check.
  - Missing skills.

Actions available:

- Filter jobs.
- Reset filters.
- Add manual company/job URL to inbox.
- Import manual URL.
- Dismiss manual URL.
- Open job apply URL.

Current UX strengths:

- The page surfaces fit evidence, not just scores.
- Manual URL inbox is a useful fallback when scanners miss a source.
- Prioritization counts help explain role quality.

Current UX problems:

- There is no direct "Save to applications" action on the Jobs page.
- Job detail is inline in a long list.
- Match evidence can become dense and repetitive.
- Manual URL inbox and job review compete for attention.
- Filter state is basic and not persistent beyond URL params.

Designer recommendations:

- Add a job detail drawer:
  - Full job description.
  - Match breakdown.
  - Evidence.
  - Missing skills.
  - Save/skip buttons.
  - Notes.
- Add primary actions to each job:
  - Save application.
  - Dismiss/ignore.
  - Open role.
  - Add feedback.
- Move manual URL inbox into an "Add URL" drawer or a compact top utility panel.
- Consider a split view:
  - Left: job list.
  - Right: selected job detail and actions.
- Let users filter by company priority, source health, posted date, first seen date, and "new since last visit".

## Route: Profile

Path: `/profile`

File: `src/app/profile/page.tsx`

Purpose:

The profile is the reusable context for matching, title generation, search strategy, and future application artifacts. It turns a resume/CV into structured developer search data.

What the user sees:

- Page header: "Profile".
- "Generate titles" button.
- Notices/errors for profile actions.
- Backend unavailable state.
- Five metric cards:
  - Complete.
  - Skills.
  - Target titles.
  - Claims.
  - Confirmed.
- Manual profile form:
  - Full name.
  - Headline.
  - Location.
  - Remote preference.
  - Target locations.
  - Preferred work modes.
  - Skills.
  - Compensation.
  - GitHub.
  - LinkedIn.
  - Portfolio.
  - Summary.
  - Dealbreakers.
  - Role framing.
- Resume import panel:
  - Large textarea for resume/CV text.
  - Import resume button.
- Markdown files panel:
  - `cv.md`.
  - `profile.md`.
  - `profile.yml`.
  - Save markdown.
- Structured profile panel:
  - Proof points.
  - Skill inventory.
  - Career timeline.
- Search strategy panel:
  - Role families.
  - Title keywords.
  - Negative keywords.
  - Seniority.
  - Locations.
  - Work modes.
  - Notes.
  - Generate.
  - Apply to companies.
- Target titles panel:
  - Title.
  - Status.
  - Fit bucket.
  - Confidence score.
  - Knowledge accuracy.
  - Evidence.
  - Accept/reject actions.
  - Apply accepted titles to company filters.
- Claims panel:
  - Extracted claims.
  - Claim type.
  - Status.
  - Confirm/reject actions.

Actions available:

- Save manual profile fields.
- Import resume text.
- Save markdown files.
- Generate target titles.
- Accept/reject target titles.
- Apply accepted titles to company filters.
- Generate search strategy.
- Apply search strategy to company filters.
- Confirm/reject claims.

Current UX strengths:

- The profile covers both unstructured files and structured search data.
- Target titles include knowledge accuracy, which is important for not overclaiming.
- Search strategy can directly improve company filters.

Current UX problems:

- The page is long and form-heavy.
- Three markdown editors shown at once consume a lot of space.
- Resume import and manual profile editing are separate but visually equal.
- Generated data review needs stronger workflow affordances.
- Accept/reject controls are small and repetitive.

Designer recommendations:

- Use tabs inside Profile:
  - Overview.
  - Resume import.
  - Profile fields.
  - Files.
  - Target titles.
  - Claims.
  - Search strategy.
- Use a review queue for generated titles and claims.
- Put markdown files in an editor drawer or tabbed editor, not three columns by default.
- Add "profile readiness checklist" showing missing fields.
- Add clear "apply to companies" preview before it updates company filters.
- Treat generated titles/claims as draft suggestions requiring confirmation.

## Route: Applications

Path: `/applications`

File: `src/app/applications/page.tsx`

Purpose:

The pipeline for roles the user saved, applied to, or chose to skip. It also hosts generated application artifacts, interview prep, and offer support.

What the user sees:

- Page header: "Applications".
- Link back to Today.
- Notices/errors.
- Backend unavailable state.
- Four metric cards:
  - Applications.
  - Active.
  - Follow-ups.
  - Artifacts.
- Kanban-like lanes:
  - Saved.
  - Applying.
  - Applied.
  - Interviewing.
  - Offer.
  - Rejected.
  - Withdrawn.
  - Skipped.
- Application cards:
  - Job title link.
  - Company and location.
  - Status selector.
  - Next action input.
  - Follow-up date input.
  - Notes textarea.
  - Save button.
  - Generated artifacts panel.
  - Interview and offer prep panel.

Actions available:

- Update application status.
- Update next action.
- Update follow-up date.
- Update notes.
- Generate application tailoring artifacts.
- Approve/reject artifacts.
- Generate interview prep.
- Generate offer support.
- Open role URL.

Current UX strengths:

- Pipeline states are clear.
- Application card stores practical fields.
- Generated artifacts are colocated with the application.

Current UX problems:

- Eight lanes are too many for a horizontal grid, especially on smaller screens.
- Cards contain full edit forms, artifacts, prep, and offer controls all at once.
- There is no focused application detail page/drawer.
- Drag-and-drop is not implemented.
- Artifact content is previewed inline and can overwhelm cards.

Designer recommendations:

- Use a pipeline board with fewer visible lanes or horizontal scroll:
  - Saved.
  - Applying.
  - Applied.
  - Interview.
  - Offer.
  - Closed.
- Use a detail drawer for editing status, notes, follow-ups, artifacts, prep, and offer support.
- Make lane cards compact:
  - Role.
  - Company.
  - Next action.
  - Follow-up date.
  - Status.
- Move generated artifacts into a tab inside the detail drawer.
- Support quick status changes from the card.
- Add due/follow-up grouping for time-sensitive applications.

## Route: Agents

Path: `/agents`

File: `src/app/agents/page.tsx`

Purpose:

The AI runtime and audit surface. This is where users can configure providers, start runs, inspect runtime status, review artifacts, approve decisions, and audit what the system did.

What the user sees:

- Page header: "Agents".
- Start run form in the header:
  - Agent type.
  - Provider.
  - Model.
  - Tool policy.
  - Consent checkbox.
  - Run Agent button.
- Notices/errors.
- Backend unavailable state.
- Four metric cards:
  - Runs.
  - Succeeded.
  - Failed.
  - Queued.
- Runtime controls panel:
  - Execution mode.
  - Queue batch size.
  - Running count.
  - Provider runtime cards with daily usage and budget.
- Run history panel:
  - Run ID and agent type.
  - Status.
  - Provider.
  - Summary or safe error.
  - Tool policy.
  - Prompt version.
  - Requested time.
  - Model.
  - Cancel.
  - Retry.
  - Steps.
  - Permissions.
  - Runtime invocations.
  - Decisions.
  - Artifacts.
  - Audit logs.
- Provider settings panel:
  - Enable/disable provider.
  - Consent required.
  - Model name.
  - Default tool policy.
  - Daily run limit.
  - Monthly budget cents.
  - Estimated cents per run.
  - Notes.
  - Save provider.

Actions available:

- Start an agent run.
- Update provider settings.
- Cancel queued/running/waiting runs.
- Retry a run.
- Approve/reject agent decisions.

Current UX strengths:

- The page exposes provider state, consent, budgets, and run history.
- Auditability is visible, which is important for trust.
- It makes clear that agents are not magic hidden automation.

Current UX problems:

- Starting an agent run from the header is too dense.
- Provider settings and run history compete for attention.
- Audit details can be overwhelming.
- Consent and tool policy need more explicit risk communication.
- Decision approval UI should feel safer and more intentional.

Designer recommendations:

- Use a "New agent run" drawer/wizard:
  - Choose task.
  - Choose provider/model.
  - Review permissions.
  - Confirm consent.
- Use run detail drawer:
  - Timeline.
  - Artifacts.
  - Decisions.
  - Runtime calls.
  - Audit logs.
- Keep provider settings in Settings or a dedicated Agents settings tab.
- Make risky tool policies visually distinct.
- Add clear empty states explaining what agents can currently do.
- Use LangSmith link/status if tracing is configured.

Important product boundary:

- Agentic workflows should remain support infrastructure, not the main user value.
- No auto-apply, no unconfirmed claims, no autonomous outreach.
- For future durable workflows, LangGraph may be appropriate for multi-step flows like scan, classify, compare profile, recommend, wait for approval, draft application.

## Route: Analytics

Path: `/analytics`

File: `src/app/analytics/page.tsx`

Purpose:

Signal quality review. This page helps answer whether Job Scout is giving useful alerts or just adding job-search noise.

What the user sees:

- Page header: "Analytics".
- Suggestions count badge.
- Weekly review button.
- Notices/errors.
- Backend unavailable state.
- Four metric cards:
  - Tracked companies.
  - Alerts.
  - Feedback.
  - Failing sources.
- Weekly review panel:
  - Summary.
  - Recommendations.
  - Risks.
  - Metrics snapshot.
- Company source quality panel:
  - Company name.
  - Source health.
  - Noisy/stale badges.
  - Usefulness score.
  - Scan counts.
  - Alert counts.
  - Application counts.
  - Feedback counts.
- Feedback inbox:
  - Unlabeled alert candidates.
  - Relevant/maybe/irrelevant buttons.
  - Reason.
  - Tags.
- Platform quality:
  - Source platform.
  - Active companies.
  - Scan success rate.
  - Alerts.
  - Feedback.
  - Usefulness.
- Review signals:
  - Noisy signals.
  - Filter suggestions.
- Recent feedback:
  - Past labels.

Actions available:

- Generate weekly review.
- Mark alert usefulness as relevant, maybe, or irrelevant.
- Add reason and tags to feedback.
- Navigate to company context.
- Open alert/job links where available.

Current UX strengths:

- This directly addresses the product risk: adding more job noise.
- Feedback loop is present.
- Company and platform quality are visible.

Current UX problems:

- The page is analytical but not action-oriented enough.
- Filter suggestions are review-only and need clearer next steps.
- Feedback labeling is embedded in a dense analytics page.
- Weekly review snapshot uses raw JSON display.

Designer recommendations:

- Separate "Signal Review" from "Analytics":
  - Signal Review: actionable feedback queue.
  - Analytics: trends and source quality.
- Add source scorecards with recommended actions:
  - Pause company.
  - Tighten filters.
  - Lower priority.
  - Keep monitoring.
- Replace raw JSON with readable metric summaries.
- Use charts sparingly and only where they guide action.
- Surface "missed roles" and "noisy companies" as first-class review objects after dogfood data exists.

## Route: Settings

Path: `/settings`

Files:

- `src/app/settings/page.tsx`
- `src/components/settings/settings-panels.tsx`

Purpose:

Workspace operations, diagnostics, notifications, import/export, restore, and deletion.

What the user sees:

- Page header: "Settings".
- Backend online/down badge.
- Notices/errors.
- Diagnostics panel:
  - Backend health.
  - Database.
  - Worker.
  - Scheduler.
  - LangSmith.
  - Notifications.
  - MTEANE.
  - AI config.
  - SMTP config.
  - Redaction.
  - Core counts.
- Notification preferences panel:
  - Quiet hours enabled.
  - Quiet hours start/end.
  - Timezone.
  - Digest enabled.
  - Digest frequency.
  - Digest delivery time.
  - Digest channel.
- Export panel:
  - Generate JSON.
  - Export textarea.
  - Download JSON link.
- Import company watchlist panel:
  - Sample JSON.
  - Import watchlist.
- Restore workspace panel:
  - Paste full workspace export JSON.
  - Restore workspace.
- Delete personal data panel:
  - Confirmation phrase.
  - Delete data button.

Actions available:

- Update notification preferences.
- Generate export JSON.
- Download export JSON.
- Import company watchlist JSON.
- Import full workspace export.
- Delete all personal data with confirmation phrase.

Current UX strengths:

- Diagnostics are visible and broad.
- Export/import/delete flows are present.
- Destructive delete has a confirmation phrase.

Current UX problems:

- Settings mixes operational health, backup, notifications, and danger zone in one long page.
- Export displays a huge JSON textarea inline.
- Restore and delete are visually close to normal settings.
- Diagnostics cards can be hard to interpret for non-backend users.

Designer recommendations:

- Use settings tabs:
  - Health.
  - Notifications.
  - Data ownership.
  - Integrations.
  - Danger zone.
- Export should be a clear flow:
  - Generate.
  - Download.
  - Copy.
  - Last generated timestamp.
- Restore should be a guided flow:
  - Upload/paste JSON.
  - Validate.
  - Preview counts.
  - Confirm import.
- Delete should be isolated in a danger-zone screen or modal.
- Diagnostics should provide recommended fixes, not just raw status.

## Backend-Down Behavior

Most pages use `toApiResult` and show route-specific `ErrorState` components instead of crashing.

Current backend-down experiences:

- Today: shows Backend API unavailable for company tracking data.
- Companies: shows backend URL and company loading failure.
- Jobs: shows jobs unavailable and discovery inbox unavailable separately.
- Profile: shows profile unavailable.
- Applications: shows applications unavailable.
- Agents: shows settings/runtime/history unavailable.
- Analytics: shows analytics unavailable.
- Settings: shows diagnostics errors and backend status.

Designer recommendation:

- Add a unified backend-down component with:
  - Backend API URL.
  - Whether frontend env is configured.
  - Suggested local command.
  - Link to Settings.
  - Retry action.

## Notice and Error Pattern

Mutating actions redirect back to the page with query params such as:

- `company_added=1`
- `company_error=...`
- `today_notice=...`
- `profile_notice=...`
- `applications_notice=...`
- `agent_notice=...`
- `analytics_notice=...`
- `settings_notice=...`

This works, but designers should know:

- These messages appear as top-of-page banners.
- There is no toast system.
- There is no inline form validation except some server-action redirects.
- Long errors can become wide text.

Recommendation:

- Use a consistent toast/banner pattern.
- Keep destructive/action failures near the action source when possible.
- Consider optimistic pending states for long-running scan/agent actions.

## Current Action Inventory

### Today

- Run due scans.
- Save alert as application.
- Skip alert.
- Mark alert read.
- Dismiss alert.
- Complete Today action.
- Dismiss Today action.
- Open role.

### Companies

- Add company.
- Edit company details.
- Edit filters.
- Save company changes.
- Scan company.
- Generate intelligence.
- Pause company.
- Resume company.
- Delete company.
- Open careers URL.

### Jobs

- Search jobs.
- Filter by work mode.
- Filter by priority.
- Add manual URL.
- Import manual URL.
- Dismiss manual URL.
- Open job URL.

### Profile

- Save profile.
- Import resume.
- Save markdown files.
- Generate target titles.
- Accept target title.
- Reject target title.
- Apply accepted titles to companies.
- Generate search strategy.
- Apply search strategy to companies.
- Confirm claim.
- Reject claim.

### Applications

- Update application status.
- Save next action.
- Save follow-up date.
- Save notes.
- Generate tailoring artifacts.
- Approve artifact.
- Reject artifact.
- Generate interview prep.
- Generate offer support.
- Open role.

### Agents

- Start agent run.
- Update provider settings.
- Cancel run.
- Retry run.
- Approve agent decision.
- Reject agent decision.

### Analytics

- Generate weekly review.
- Mark alert relevant.
- Mark alert maybe.
- Mark alert irrelevant.
- Add feedback reason.
- Add feedback tags.

### Settings

- Save notification preferences.
- Generate export JSON.
- Download export JSON.
- Import company watchlist.
- Restore workspace.
- Delete all personal data.

## Recommended Redesign Information Architecture

The current navigation is reasonable, but the internal screen layouts should shift toward task-specific workspaces.

Suggested top-level nav:

- Today
- Companies
- Jobs
- Applications
- Profile
- Analytics
- Agents
- Settings

Suggested interaction patterns:

- Today: inbox + right detail drawer.
- Companies: table/list + company detail drawer.
- Jobs: list + job detail drawer.
- Applications: compact pipeline + application detail drawer.
- Profile: tabs + review queues.
- Analytics: action-oriented signal review + source scorecards.
- Agents: run history + run detail drawer + separate provider settings.
- Settings: tabbed settings + guided import/export/restore flows.

## Drawer and Modal Recommendations

Use drawers when the user is working from a list and needs detail without losing context:

- Company details and filters.
- Job details and save/skip.
- Alert triage.
- Application details.
- Agent run details.
- Generated artifact detail.

Use modals for short confirmation or dangerous actions:

- Delete company.
- Delete all personal data.
- Confirm restore.
- Approve high-risk agent decision.

Use tabs for large long-lived sections:

- Profile editor sections.
- Settings sections.
- Agent run detail subviews.

Use inline controls only for fast, low-risk updates:

- Status dropdowns.
- Simple filters.
- Feedback rating.
- Pause/resume when clearly reversible.

## Designer Prompt

Use this prompt when asking a designer or design agent to redesign the UI:

```text
We are designing Job Scout V2, a developer-centric personal job tracking app. The user's main problem is missing when favorite companies post relevant roles, not needing another generic job board search. The product monitors selected company career pages, tracks source health, surfaces new-role alerts, ranks jobs against the user's developer profile, saves promising roles into an application pipeline, supports manual URL capture, and gives analytics on whether alerts are useful or noisy.

The current frontend is a Next.js app with these routes: Today, Companies, Jobs, Applications, Profile, Agents, Analytics, Settings. It has a left desktop sidebar and mobile horizontal nav. Pages use dense cards, tables, forms, metric cards, and status badges. Most actions are server-rendered forms with top-of-page success/error banners.

Design the app as a quiet, utilitarian, high-trust workspace for a developer using it repeatedly during a job search. Avoid landing-page or marketing aesthetics. Prefer dense but readable operational layouts, compact tables, focused detail drawers, clear statuses, and fast triage actions.

Primary workflows:
1. Add favorite companies and career URLs.
2. Scan companies and inspect source health.
3. Review new-role alerts in Today.
4. Save relevant roles as applications or skip irrelevant ones.
5. Review jobs with match evidence and missing skills.
6. Maintain a developer profile, target titles, claims, and search strategy.
7. Track applications, notes, next actions, follow-ups, generated artifacts, interview prep, and offer support.
8. Review analytics to see whether sources and alerts are useful or noisy.
9. Configure agents, provider budgets, permissions, consent, and audit logs.
10. Export, restore, and delete personal data.

Important product boundaries:
- No auto-apply.
- No autonomous outreach.
- AI-generated claims must be reviewed/confirmed.
- Agent actions require consent and auditability.
- Source health and missed/noisy alerts are central to trust.

Recommended redesign pattern:
- Today should be an inbox with a selected alert/action detail drawer.
- Companies should be a compact watchlist table with a company detail drawer for filters, scans, intelligence, and dangerous actions.
- Jobs should be a list/detail split where the detail drawer shows match breakdown, evidence, missing skills, and Save/Skip/Open actions.
- Applications should be a compact pipeline board with an application detail drawer.
- Profile should be tabbed: Overview, Resume Import, Profile Fields, Files, Target Titles, Claims, Search Strategy.
- Agents should separate run creation, run history, run details, provider settings, and audit views.
- Analytics should focus on source scorecards, noisy signals, feedback queue, and recommended filter/source actions.
- Settings should be tabbed into Health, Notifications, Data Ownership, Integrations, Danger Zone.

Design must include states for backend down, empty data, loading/pending actions, failed scans, paused companies, unscanned companies, noisy alerts, low-confidence matches, pending agent approval, missing API keys, and destructive confirmations.
```

## Highest-Value UI Improvements

1. Add detail drawers for Companies, Jobs, Applications, Agents, and Today alert triage.
2. Make Today the fast triage inbox instead of a dense dashboard.
3. Make Companies the strongest source-monitoring surface with filtering, grouping, and source-health operations.
4. Add direct Save/Skip actions to Jobs.
5. Split Settings into tabs and make restore/delete safer.
6. Convert Profile into tabbed editor/review flows.
7. Make Analytics action-oriented, not just descriptive.
8. Add consistent pending/loading states for scans and agent runs.
9. Add a unified backend-down recovery component.
10. Clarify AI/agent risk levels with better permission and consent UI.

## Current Frontend File Map

- `src/app/layout.tsx`: root layout and app shell wrapper.
- `src/app/page.tsx`: Today dashboard and triage.
- `src/app/companies/page.tsx`: company watchlist and source health.
- `src/app/jobs/page.tsx`: job review and manual URL inbox.
- `src/app/profile/page.tsx`: candidate profile, resume import, titles, claims, strategy.
- `src/app/applications/page.tsx`: application pipeline and prep artifacts.
- `src/app/agents/page.tsx`: agent runtime, provider settings, runs, audit.
- `src/app/analytics/page.tsx`: source quality, feedback, weekly review.
- `src/app/settings/page.tsx`: diagnostics, notifications, import/export, delete.
- `src/app/*/actions.ts`: server actions for each route.
- `src/components/shell/`: app shell and nav link.
- `src/components/companies/`: company-specific UI.
- `src/components/settings/`: settings panels.
- `src/components/ui/`: shared primitive components.
- `src/lib/api/`: backend API client, endpoint wrappers, and shared TypeScript types.

