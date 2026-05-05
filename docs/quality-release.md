# Quality And Release Gates

Run the full gate before merging or deploying v2 work.

## Backend

```bash
cd Backend
../.venv/bin/python manage.py makemigrations --check --dry-run
../.venv/bin/python manage.py check
JOB_SCOUT_REQUIRE_AUTH=True JOB_SCOUT_API_TOKEN=test-token ../.venv/bin/python manage.py check --deploy
../.venv/bin/python manage.py test
```

Coverage focus:

- Scraper source detection and dedupe behavior.
- Company filters and source-health transitions.
- Match scoring and user correction learning.
- Profile import/profile transform output.
- Export, restore, delete-all, and redaction audit.

## Frontend

```bash
cd Frontend
npm run lint
npm run test:interactions
npm run test:a11y
npm run build
```

The interaction contract checks that Today, Companies, Jobs, Profile, Applications, Agents, Analytics, and Settings expose the expected data/actions. The accessibility contract checks route page context, landmark structure, and labeled high-risk controls.

## E2E Smoke

With backend and frontend running:

```bash
./scripts/smoke-test.sh
```

Set `SMOKE_PROFILE_IMPORT=1` only on disposable data because profile import updates the singleton local profile.

## Docker Gate

On a machine with Docker installed:

```bash
docker compose config
docker compose up --build
docker compose --profile mteane config
```

The MTEANE profile must show `mteane-worker` waiting on a healthy `mteane-api` service.

## Rollback Checklist

- Stop workers/schedulers first.
- Preserve current logs and failed request samples.
- Restore database backup if a schema migration failed.
- Restore `job-scout-export.json` through `/api/import/workspace` only after schema compatibility is confirmed.
- Re-run backend, frontend, and smoke gates before resuming scans.
