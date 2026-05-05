# Smoke Test Checklist

Run this after local setup, after Render deploys, and before tagging a release.

## Automated Smoke

```bash
BACKEND_URL=http://127.0.0.1:8000/api FRONTEND_URL=http://127.0.0.1:3000 ./scripts/smoke-test.sh
```

For Render:

```bash
BACKEND_URL=https://job-scout-backend.onrender.com/api FRONTEND_URL=https://job-scout-frontend.onrender.com ./scripts/smoke-test.sh
```

For deployed instances with `JOB_SCOUT_REQUIRE_AUTH=True`:

```bash
BACKEND_URL=https://api.example.com/api FRONTEND_URL=https://app.example.com BACKEND_API_TOKEN=<token> ./scripts/smoke-test.sh
```

## Manual Smoke

1. Open the frontend.
2. Confirm Today loads without a 500.
3. Open Companies.
4. Add a temporary company.
5. Run a scan dry-run from Today or manual rescan from Companies.
6. Open Alerts or Today and confirm alert endpoints load.
7. Open Profile and confirm optional profile setup loads.
8. Open Agents and confirm CLI runtimes show as worker-only/disabled.
9. Open Analytics and confirm source metrics load.
10. Open Settings and generate an export.
11. Delete the temporary company.

## API Smoke

```bash
curl -fsS "$BACKEND_URL/health"
curl -fsS "$BACKEND_URL/companies"
curl -fsS "$BACKEND_URL/scans"
curl -fsS "$BACKEND_URL/alerts"
curl -fsS "$BACKEND_URL/export"
curl -fsS "$BACKEND_URL/analytics"
```

## Failure Rules

- Any 500 response blocks release.
- A failing scrape for an unsupported test URL does not block release if scan jobs record a readable failure.
- Missing optional AI keys do not block release.
- Exports must not contain secret values.
