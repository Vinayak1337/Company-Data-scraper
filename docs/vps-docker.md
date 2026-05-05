# VPS And Local Docker Deployment

Job Scout's Docker path is a Compose stack, not one process inside one container. That keeps Django, scheduled scans, agent queue work, Postgres, and optional MTEANE processes restartable independently while still being easy to run on a VPS.

## Services

- `backend`: Django API, Gunicorn, migrations on boot.
- `scanner`: periodic `scan_due_companies` loop.
- `agent-worker`: periodic `process_agent_queue` loop.
- `db`: Postgres for Job Scout.
- `mteane-*`: optional event automation services behind the `mteane` profile.

## Local Start

```bash
docker compose up --build
```

The backend is available at `http://127.0.0.1:8000/api/health`.

Run the frontend separately during local development:

```bash
cd Frontend
npm install
BACKEND_API_BASE_URL=http://127.0.0.1:8000/api npm run dev
```

## VPS Start

1. Point a reverse proxy at the backend container on port `8000`.
2. Set production values in the shell, an `.env` file, or your VPS secret manager:

```bash
SECRET_KEY=<generated-secret>
DEBUG=False
ALLOWED_HOSTS=api.example.com
CSRF_TRUSTED_ORIGINS=https://app.example.com
JOB_SCOUT_REQUIRE_AUTH=True
JOB_SCOUT_API_TOKEN=<generated-api-token>
POSTGRES_PASSWORD=<generated-postgres-password>
SCANNER_ENABLED=True
# Optional AI tracing
LANGSMITH_TRACING=False
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=job-scout-v2
```

3. Start the stack:

```bash
docker compose up -d --build
```

4. Run the smoke test from your workstation:

```bash
BACKEND_URL=https://api.example.com/api FRONTEND_URL=https://app.example.com BACKEND_API_TOKEN=<generated-api-token> ./scripts/smoke-test.sh
```

## Operational Notes

- Back up the `job-scout-postgres` volume before upgrades.
- Stop `scanner` and `agent-worker` before risky migrations or restores.
- Keep `SCANNER_ENABLED=True` on the backend service when the separate scanner container is deployed so diagnostics can report scheduler readiness accurately.
- Keep `SCAN_INTERVAL_SECONDS` conservative until dogfood proves source quality.
- Use `DATABASE_SSLMODE=disable` for the local Compose Postgres service.
- Use managed Postgres with SSL for hosted production when possible.
