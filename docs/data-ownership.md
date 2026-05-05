# Data Ownership

Job Scout is local-first. The workspace export is the user-owned backup format, and the delete flow is intentionally explicit.

## Export

`GET /api/export` returns a JSON snapshot with:

- Profile, target titles, claims, and search strategy.
- Companies, jobs, alerts, scan summaries, and source-health metadata.
- Applications, artifacts, interview prep, offer support, and Today actions.
- Agent provider metadata, agent runs, steps, artifacts, decisions, permissions, runtime invocation summaries, and audit logs.
- Analytics feedback, weekly reviews, match corrections, and learning changes.
- Company intelligence, recruiter contacts, and manual URL inbox items.

Secrets are not exported. Provider records include env-var names and configured/missing flags only.

## Restore

`POST /api/import/workspace` accepts the complete export object. It upserts stable user-owned records by URL, job apply URL, profile title/claim text, application job, and related IDs where possible.

Restore behavior by domain:

- `profile`, `target_titles`, `claims`, `search_strategy`: restored and upserted.
- `companies`, `jobs`, `applications`, `application_artifacts`: restored and upserted.
- `interview_preps`, `offer_support`, `company_intelligence`, `recruiter_contacts`: restored.
- `notification_preferences`, `manual_url_inbox`, `weekly_reviews`, `job_matches`, `learning_changes`, `match_score_corrections`: restored.
- `scan_logs`, `scan_jobs`, `alerts`: restored as historical records where company/job mapping is available.
- `agent_providers`: restored without secrets.
- `agent_runs`: restored with redacted snapshots, steps, artifacts, decisions, permissions, runtime invocations, and audit logs.

## Delete

`POST /api/data/delete-all` requires:

```json
{"confirmation":"DELETE ALL PERSONAL DATA"}
```

It removes profile data, companies, jobs, applications, agents, analytics, notifications, manual inbox items, intelligence, interview/offer support, and provider settings. Default provider settings are recreated without secrets.

## Redaction Audit

`GET /api/redaction-audit` reports the current redaction policy:

- Diagnostics expose status flags, not secret values.
- Runtime invocation payloads are scrubbed before storage and redacted again during export serialization.
- API/export serialization redacts CV/profile markdown from agent snapshots.
- Scan-log exports omit raw scraper error messages by default.
