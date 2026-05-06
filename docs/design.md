# V3 Design

## Product Shape

V3 is an operational console for one job-search loop:

Profile setup -> company watchlist -> source discovery -> local run-once crawls -> match review -> email notification -> feedback tuning.

The interface should be quiet, dense, and repeatable. This is not a landing page and not a CRM. It should help the user answer:

- Is my setup complete enough for AI matching?
- Which companies are being watched?
- Which companies need source review?
- Which jobs are worth applying to?
- Why did the system notify me?
- How do I tune the matches?

## Information Architecture

### Today

Purpose: daily operating surface.

Content:

- Setup readiness checklist.
- Active company count.
- Companies needing source review.
- Due crawl count.
- New high-fit matches.
- Latest crawl runs.
- Notification readiness.

Primary actions:

- Complete profile.
- Open settings.
- Import company CSV.
- Run due crawls.
- Review matches.

### Profile

Purpose: create the source of truth for matching.

Sections:

- Identity: name, headline, location.
- Resume import.
- Target roles and seniority.
- Skills and proof points.
- Work mode and location preferences.
- Dealbreakers and negative signals.
- AI-generated target titles/search strategy.

Design principle:

- Show setup completeness prominently.
- Make missing fields obvious.
- Keep generated AI claims reviewable.

### Companies

Purpose: manage the watchlist and job sources.

Sections:

- CSV import.
- Watchlist table.
- Company details drawer.
- Source discovery status.
- Primary jobs source.
- Crawl controls.

Company states:

- `active`: included in scheduled crawls.
- `inactive`: saved but skipped.
- `needs_source`: no usable jobs source yet.
- `needs_review`: AI found a low-confidence source.
- `failing`: recent crawl failures.

Primary actions:

- Import CSV.
- Toggle active/inactive.
- Discover source.
- Set source manually.
- Run now.

### Jobs

Purpose: review matches, not every job equally.

Sections:

- Filters: priority, score, company, status.
- Match list with score, confidence, and reason.
- Detail panel with evidence and gaps.
- Feedback controls.

Job states:

- `new`
- `notified`
- `saved`
- `dismissed`
- `stale`

Primary actions:

- Open apply URL.
- Mark good match.
- Mark bad match.
- Dismiss.
- Save for later.

### Settings

Purpose: configure AI and notifications.

Sections:

- AI provider readiness, split between API providers and local-only CLI providers. Setup is read-only in the web UI.
- Matching preferences.
- Notification preferences.
- Email/digest settings.
- Data import/export/delete.

Primary actions:

- Show the terminal command for provider setup.
- Set minimum score.
- Set minimum confidence.
- Set frequency.
- Test email configuration.
- Run the local setup/status CLI.

## UI Direction

Tone:

- Utilitarian.
- Calm.
- Dense.
- Built for repeated scanning.

Visual rules:

- No marketing hero.
- No decorative cards around entire sections.
- Tables and split detail panes over large card stacks.
- Small typography in operational panels.
- Icons for actions where obvious: upload, play, pause, refresh, mail, settings.
- Text buttons only for explicit commands.
- Stable widths for score badges, toggles, and action buttons.

Navigation:

- Primary: Today, Companies, Jobs.
- Secondary: Profile, Settings.
- AI runtime belongs inside Settings, not as a separate top-level destination.

## Backend Design

### Company Source Discovery

The source discovery service should accept a company and return candidates:

```text
input: company name, domain, homepage URL, existing careers URL
output: candidate source URLs, platform, confidence, evidence, notes
```

Discovery rules:

- Manual source always wins.
- Known ATS URLs get high confidence.
- Homepage `/careers`, `/jobs`, `/open-roles`, `/join-us` get medium confidence.
- Search-derived sources require review unless confidence is high.
- Failed discovery should set a human-readable reason.

### Crawling

Each crawl run records:

- Company.
- Source.
- Trigger.
- Status.
- Started/finished timestamps.
- Jobs found/created/updated/closed.
- Error message.

The crawler should not directly notify the user. It should create/update jobs and then ask matching/notification services what should happen.

For V3, the authoritative recurring workflow is a terminal command:

```bash
./jobscout run-once --force
```

That command is the bridge between local setup and any future hosted scheduler. UptimeRobot, cron, or background workers should call equivalent server behavior only after the local command proves the crawl, match, notification, and email path.

### Local CLI Providers

CLI providers are not hosted providers. They depend on local login state and must be treated as local worker tools.

Rules:

- `gemini_cli`, `claude_code_cli`, and `opencode` are local-only.
- `codex_cli` is also supported as a local-only brain provider.
- They are configured through `./jobscout providers`, which writes `Backend/.env`.
- They should never be enabled in `JOB_SCOUT_RUNTIME_ENV=hosted`.
- The web app can display their readiness, but it should not imply they can run on hosted Render/web services.
- Setup is done from the terminal with `./jobscout setup`.
- Backend and frontend runtime starts require the local `.jobscout/setup.json` marker written by `./jobscout init`.

### Matching

The matcher has two layers:

1. Feature scorer.
2. Agent review.

Feature scorer:

- Extract title, skill, seniority, location, work-mode, dealbreaker, source, and feedback features.
- Produce scores and evidence.
- Keep all weights explicit.

Agent review:

- Uses the feature payload and profile snapshot.
- Decides whether the role clears the user's current notification threshold.
- Adds explanation and uncertainty notes.
- Cannot hide deterministic evidence.

### Notifications

Notification selection should be deterministic after match review:

```text
notify if:
  score >= user minimum score
  confidence >= user minimum confidence
  job not already notified
  company active
  notification preference enabled
```

The AI can recommend a threshold, but the saved user preference is the guardrail.

## API Design

Keep the V3 API small:

- `GET /api/health`
- `GET /api/diagnostics`
- `GET/PATCH /api/profile`
- `GET/PATCH /api/settings/matching`
- `GET/PATCH /api/notifications/preferences`
- `GET/POST /api/companies`
- `POST /api/companies/import-csv`
- `GET/PATCH/DELETE /api/companies/:id`
- `POST /api/companies/:id/discover-source`
- `POST /api/companies/:id/sources`
- `PATCH/DELETE /api/companies/:id/sources/:source_id`
- `POST /api/companies/:id/crawl`
- `POST /api/crawls/run-due`
- `GET /api/crawls`
- `GET /api/jobs`
- `GET /api/jobs/:id`
- `POST /api/jobs/:id/feedback`
- `GET /api/agents/providers`
- `PATCH /api/agents/providers/:provider`
- `POST /api/agents/runs`
- `GET /api/agents/runs`

Remove V2 API groups:

- Applications.
- Interview prep.
- Analytics.
- Company intelligence.
- Manual URL inbox.
- Today actions.

## Data Design

### CandidateProfile

Stores user profile and derived profile documents.

Must support:

- Setup completeness.
- Skills.
- Target titles.
- Locations.
- Work modes.
- Dealbreakers.
- Resume/profile markdown.

### UserSearchPreference

Stores matching controls:

- Minimum score.
- Minimum confidence.
- Match strictness.
- Digest frequency.
- Excluded keywords.
- Preferred seniority.
- Preferred role families.

### Company

Stores watchlist item:

- Name.
- Domain/homepage.
- Active flag.
- Priority.
- Source discovery state.
- Last crawl state.
- Notes.

### CompanyJobSource

Stores discovered or manual job source:

- URL.
- Platform.
- Discovery method.
- Confidence.
- Primary flag.
- Status.

### CrawlRun

Stores periodic/manual crawl execution.

### Job

Stores normalized jobs and lifecycle state.

### JobMatch

Stores match score, feature payload, evidence, agent notes, priority, and notification recommendation.

### MatchFeedback

Stores user feedback that changes future matching.

### NotificationEvent

Stores sent/skipped notification decisions for dedupe and audit.

## Cleanup Rules

- Delete pages whose routes are no longer in navigation.
- Delete backend apps removed from `INSTALLED_APPS`.
- Delete imports and serializers that only support removed features.
- Delete docs that claim V2-only features are current.
- Keep V2 docs only if clearly marked historical.
- Keep tests only if they exercise V3 behavior.
