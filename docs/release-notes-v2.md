# Job Scout V2 Release Notes

## What V2 Does

Job Scout V2 is a self-hosted company job radar for developers. It watches favorite companies, tracks source health, detects new roles, ranks jobs against a user-owned profile, and turns real opportunities into next actions.

## Highlights

- Next.js app shell with Today, Companies, Jobs, Profile, Applications, Agents, Analytics, and Settings.
- Django API with company watchlist, scans, alerts, applications, profile studio, matching, analytics, and data ownership endpoints.
- Deterministic match reports with evidence, gaps, confidence, and user corrections.
- Agent orchestrator with provider settings, consent/budget controls, artifacts, decisions, permissions, audit logs, retry/cancel, and worker queue mode.
- Optional LangSmith tracing for redacted agent-run observability; LangChain is not required.
- Public-source-only company/recruiter intelligence.
- Interview prep, STAR story seeds, offer comparison support, and manual compensation notes.
- Full export, restore, delete-all-personal-data, and redaction audit.
- Render deployment blueprint, smoke script, and CI quality workflow.

## Known Limitations

- Deterministic local agents are implemented; external AI adapter execution is still controlled/limited.
- LangGraph is intentionally deferred until durable branching/waiting workflows justify it.
- Docker Compose YAML is prepared, but final Docker runtime boot still must be verified on a machine with Docker.
- Scraper coverage is best for supported ATS/public career pages and degrades visibly when sources block or change.
- Agent decisions are review-only; accepting a decision records approval but does not auto-apply changes.
- The bookmarklet is optional and depends on browser-to-backend network access.
- Dogfood results must still validate whether the workflow beats manual checking for a real developer.

## Required Release Gate

Run:

```bash
cd Backend && ../.venv/bin/python manage.py makemigrations --check --dry-run && ../.venv/bin/python manage.py check && ../.venv/bin/python manage.py test
cd ../Frontend && npm run lint && npm run test:interactions && npm run test:a11y && npm run build
cd .. && ./scripts/smoke-test.sh
```
