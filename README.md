# Job Scout

Self-hosted developer job tracker. The `v2` branch is being reshaped into a split app:

- `Frontend/`: Next.js app for the v2 product UI.
- `Backend/`: Django/Python backend, legacy v1 HTMX UI, scraper adapters, API, and deployment files.
- `docs/`: v2 planning and build-task docs.
- `render.yaml`: Render Blueprint for the split Backend/Frontend deployment.
- `scripts/`: local and deployment smoke-test helpers.

The v2 north star is favorite-company tracking: users should not miss relevant openings posted by companies they intentionally watch.

## Current Backend Features

- Django-rendered dashboard with HTMX partial updates.
- Compiled TailwindCSS dark interface.
- Company tracking by careers or ATS URL.
- Scraper adapters for Greenhouse, Lever, Ashby, and generic HTML pages.
- Microsoft Careers job-detail URLs via structured `JobPosting` data.
- Curated top-tier companies seeded on migration.
- Local filters for title, keyword, company, location, tech stack, and work mode.
- India-first default feed with state and city filters.
- Simple JSON API.
- Render deployment files included.

## Backend Local Setup

Fast path:

```bash
cd Backend
./start.sh
```

Or:

```bash
cd Backend
npm start
```

The start script creates `.venv` if needed, installs Python deps, installs Node deps if needed, builds Tailwind, runs migrations, seeds default companies, and starts Django.

Manual setup:

```bash
cd Backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
npm install
npm run build:css
python manage.py migrate
python manage.py runserver
```

Open `http://127.0.0.1:8000`.

## Frontend Local Setup

```bash
cd Frontend
npm install
npm run dev
```

Open `http://127.0.0.1:3000`.

By default the frontend calls `http://127.0.0.1:8000/api`. Override it with:

```bash
BACKEND_API_BASE_URL=http://127.0.0.1:8000/api npm run dev
```

## Deployment

The project supports Vercel frontend plus a Docker/VPS backend stack, and still includes a split Render Blueprint with separate Backend and Frontend services plus Postgres. See [docs/deployment-readiness.md](docs/deployment-readiness.md), [docs/vps-docker.md](docs/vps-docker.md), [docs/vercel.md](docs/vercel.md), [docs/deployment.md](docs/deployment.md), [docs/mteane.md](docs/mteane.md), [docs/backup-export.md](docs/backup-export.md), and [docs/smoke-test.md](docs/smoke-test.md).

Backend stack with Docker:

```bash
docker compose up --build
```

Optional MTEANE event automation profile:

```bash
git submodule update --init --recursive
docker compose --profile mteane up --build
```

Run a local smoke test after both dev servers are up:

```bash
./scripts/smoke-test.sh
```

## Usage

Backend v1 UI:

1. Paste a careers or ATS URL such as `https://jobs.lever.co/company` or `https://boards.greenhouse.io/company`.
2. Click **Add company**.
3. Click **Scrape** on the company card.
4. Filter jobs from the dashboard.
5. Use **Open application** or **Apply** to visit the original posting.

To reseed the default company list later:

```bash
cd Backend
python manage.py seed_companies
```

## API

- `GET /api/health`
- `GET /api/jobs`
- `GET /api/jobs/<id>`
- `GET /api/companies`
- `POST /api/companies`
- `POST /api/companies/<id>/scrape`

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/companies \
  -H "Content-Type: application/json" \
  -d '{"careers_url":"https://jobs.lever.co/example","name":"Example"}'
```

## V2 Direction

The `v2` branch is reserved for favorite-company tracking, source health, scheduled scans, relevant-role alerts, and optional profile/AI support for ranking and application prep.

See [docs/v2-plan.md](docs/v2-plan.md) for the detailed v2 product plan.
See [docs/v2-build-tasks.md](docs/v2-build-tasks.md) for implementation workstreams and delegate-friendly task groups.
