# Backup And Export

Job Scout is user-owned data. The app should be useful even if the deployment is moved or deleted.

## App Export

Use the Settings page or API:

```bash
curl -fsS "$BACKEND_URL/export" > job-scout-export.json
```

The export includes:

- Companies and filters
- Jobs
- Scan logs and scan jobs
- Alerts
- Applications and Today actions
- Candidate profile data
- Agent provider metadata and redacted agent run history
- Analytics feedback

The export must not include secret environment variable values.

## Database Backup

For Render Postgres, use Render's database backup/recovery tools for point-in-time operational recovery. Keep app-level JSON exports separately because they are easier to inspect, diff, and import into a fresh app instance.

Recommended routine for a personal deployment:

- Weekly app JSON export from `/api/export`.
- Render-managed Postgres backup enabled according to the database plan.
- Export before large migrations or bulk imports.
- Export before changing scraper, profile, or agent behavior.

## Restore Strategy

`POST /api/import/workspace` restores the exported user-owned domains into a compatible schema. Runtime snapshots remain redacted, and raw scraper error messages are not exported by default.

Recommended restore order:

1. Restore the Postgres database backup when available.
2. Or create a fresh app and import the workspace JSON export.
3. Run diagnostics and spot-check companies, jobs, applications, profile data, agent runs, and analytics after restore.
