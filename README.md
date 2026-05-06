# Job Scout

Self-hosted profile-first company watchlist for job discovery and matching.

V3 focuses on one useful loop:

1. Complete profile, AI, and notification setup.
2. Import a CSV watchlist of companies.
3. Discover each company's public jobs source.
4. Periodically crawl active companies.
5. Match discovered jobs against the profile.
6. Notify the user only when a job clears score and confidence thresholds.
7. Capture feedback so future matches become stricter or looser.

## Repository Layout

- `Backend/`: Django API, scraper adapters, source discovery, matching, notifications, and agent runtime audit.
- `Frontend/`: Next.js console for Today, Companies, Jobs, Profile, and Settings.
- `docs/v3-plan.md`: detailed implementation plan.
- `docs/design.md`: V3 product, UX, backend, API, and data design.
- `docker-compose.yml`: local runtime scaffolding.
- `render.yaml`: optional hosted web scaffolding after local wiring is complete. It does not run local CLI providers or scheduled crawls.

## Current V3 Surface

- Profile setup with resume import, target titles, claims, and search strategy.
- Company watchlist with CSV import, active/inactive toggles, manual source override, and source discovery.
- Crawl runs for active companies with source health and run history.
- Weighted ML-style matching with score, confidence, evidence, threshold, and local agent summary.
- Feedback events such as good match, bad match, wrong role, wrong location, too many notifications, and want more matches.
- Notification preferences for email address, immediate/digest delivery, minimum score, and minimum confidence.
- Agent provider settings and local deterministic agent reviews for source discovery, match review, and notification review.

## Local Setup

```bash
./jobscout init
./jobscout dev
```

The root `jobscout` command manages both `Backend/` and `Frontend/`.
Use `./jobscout ...` from the repo root, or `jobscout ...` if the repo root is on your `PATH`.
`./jobscout init` writes the local setup marker at `.jobscout/setup.json`. Backend and frontend runtime commands intentionally exit before boot if that marker is missing.

```bash
./jobscout status
./jobscout providers
./jobscout setup --resume-file resume.md --watchlist-csv companies.csv
./jobscout import-watchlist --csv companies.csv
./jobscout run-once --force
./jobscout backend
./jobscout frontend
```

The backend API defaults to `http://127.0.0.1:8000/api`; the frontend defaults to `http://127.0.0.1:3000`.

Provider setup is terminal-only. `./jobscout providers` opens a numbered selector, writes `Backend/.env`, and marks the selected provider as the local Job Scout brain. CLI-based providers are local-only because they require terminal login state:

```bash
./jobscout providers --provider gemini_cli
./jobscout providers --provider claude_code_cli
./jobscout providers --provider codex_cli
```

Local email defaults to Django's console backend. Configure SMTP for real delivery:

```bash
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_HOST_USER=...
EMAIL_HOST_PASSWORD=...
DEFAULT_FROM_EMAIL="Job Scout <jobs@example.com>"
```

## Manual Frontend Local Setup

Manual frontend starts still require the root init step first:

```bash
./jobscout init
```

```bash
cd Frontend
npm install
npm run dev
```

Open `http://127.0.0.1:3000`.

Override the backend URL when needed:

```bash
BACKEND_API_BASE_URL=http://127.0.0.1:8000/api npm run dev
```

## Useful API Endpoints

- `GET /api/health`
- `GET /api/diagnostics`
- `GET/PATCH /api/profile`
- `GET/PATCH /api/notifications/preferences`
- `GET/POST /api/companies`
- `POST /api/companies/import-csv`
- `POST /api/companies/<id>/discover-source`
- `POST /api/companies/<id>/sources`
- `POST /api/companies/<id>/crawl`
- `GET /api/crawls`
- `POST /api/crawls/run-due`
- `GET /api/jobs`
- `POST /api/jobs/<id>/feedback`
- `GET/PATCH /api/agents/providers`
- `GET/POST /api/agents/runs`

Send queued notification emails:

```bash
./jobscout run-once --force
```

Run the full local periodic loop once. This crawls due active companies, creates match notification events, and sends queued emails through the configured local email backend:

```bash
./jobscout run-once --force
```

Hosted cron/uptime triggers should wait until the local loop is fully wired and tested. The included Render blueprint is web-only for now.

Example CSV import:

```bash
curl -X POST http://127.0.0.1:8000/api/companies/import-csv \
  -H "Content-Type: application/json" \
  -d '{"csv":"company,domain,active\nAcme,acme.com,true\n"}'
```

## Verification

Backend:

```bash
cd Backend
./.venv/bin/python manage.py test api scrapers_engine companies matching notifications profiles agents
```

Frontend:

```bash
cd Frontend
npm run lint
npm run build
```
