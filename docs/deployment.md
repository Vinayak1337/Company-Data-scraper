# Deployment

Job Scout v2 supports two deployment paths:

- Vercel frontend plus Docker/VPS backend stack.
- Split Render Blueprint from the repository root.

See [deployment readiness](deployment-readiness.md), [VPS Docker](vps-docker.md), [Vercel](vercel.md), and [MTEANE](mteane.md) for the current release-hardening plan.

## Render Blueprint

The Render path deploys:

- `job-scout-backend`: Django/Gunicorn web service with `rootDir: Backend`.
- `job-scout-frontend`: Next.js web service with `rootDir: Frontend`.
- `job-scout-db`: Render Postgres database connected to the backend through `DATABASE_URL`.

Render's Blueprint spec supports root-level `render.yaml`, per-service `rootDir` for monorepos, and `preDeployCommand` for migrations. The root [render.yaml](../render.yaml) uses those fields so backend and frontend builds stay isolated.

## Render Setup

1. In Render, create a Blueprint from this repository.
2. Use the repository-root `render.yaml`.
3. Let Render create the Postgres database.
4. Generate one API token and set it in both backend `JOB_SCOUT_API_TOKEN` and frontend `BACKEND_API_TOKEN`.
5. Deploy the backend first, then confirm `/api/health` returns `{"status":"ok","auth_required":true,"auth_configured":true}`.
6. Deploy the frontend and set `BACKEND_API_BASE_URL` to the backend public URL plus `/api`.
7. Add any optional AI provider or LangSmith keys only in Render environment variables.

## Backend Environment

Use [Backend/.env.example](../Backend/.env.example) as the source of truth.

Required in production:

- `SECRET_KEY`
- `DEBUG=False`
- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`
- `DATABASE_URL`
- `JOB_SCOUT_REQUIRE_AUTH=True`
- `JOB_SCOUT_API_TOKEN`

Optional:

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `GOOGLE_API_KEY`
- `GEMINI_API_KEY`
- `OPENROUTER_API_KEY`
- `DEEPSEEK_API_KEY`
- `LANGSMITH_TRACING`
- `LANGSMITH_API_KEY`
- `LANGSMITH_PROJECT`
- SMTP variables for future email delivery
- `MTEANE_ENABLED`
- `MTEANE_API_URL`
- `MTEANE_API_KEY`

## Frontend Environment

Use [Frontend/.env.example](../Frontend/.env.example).

Required:

- `BACKEND_API_BASE_URL`
- `BACKEND_API_TOKEN` when `JOB_SCOUT_REQUIRE_AUTH=True`

Example:

```bash
BACKEND_API_BASE_URL=https://job-scout-backend.onrender.com/api
BACKEND_API_TOKEN=<same-value-as-JOB_SCOUT_API_TOKEN>
```

## Local Production Check

```bash
cd Backend
../.venv/bin/python manage.py check
../.venv/bin/python manage.py test

cd ../Frontend
npm run lint
npm run build
```

Run the smoke script against local or deployed services:

```bash
BACKEND_URL=http://127.0.0.1:8000/api FRONTEND_URL=http://127.0.0.1:3000 ./scripts/smoke-test.sh
```

## Deployment Notes

- Migrations and `python manage.py check --deploy` run in `preDeployCommand`, not the backend build script.
- Render deploy is intentionally blocked when `JOB_SCOUT_REQUIRE_AUTH=True` but `JOB_SCOUT_API_TOKEN` is empty.
- The backend build script only installs dependencies, builds legacy CSS, and collects static files.
- The frontend uses `npm ci`, `npm run build`, and `npm run start`.
- CLI agent runtimes remain disabled for web requests; do not add shell-based AI execution to web services.
- Render should use separate web/background/private services for production workers and optional MTEANE components.
- A single Docker Compose stack is intended for local/VPS use, not as one multi-process Render web service.
