# Job Scout v1

Self-hosted Django + HTMX job scraper. Paste a careers or ATS URL, scrape jobs, and filter the results locally without AI or external APIs.

## Features

- Django-rendered dashboard with HTMX partial updates.
- Compiled TailwindCSS dark interface.
- Company tracking by careers or ATS URL.
- Scraper adapters for Greenhouse, Lever, Ashby, and generic HTML pages.
- Local filters for title, keyword, company, location, tech stack, and work mode.
- Simple JSON API.
- Render deployment files included.

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
npm install
npm run build:css
python manage.py migrate
python manage.py runserver
```

Open `http://127.0.0.1:8000`.

## Usage

1. Paste a careers or ATS URL such as `https://jobs.lever.co/company` or `https://boards.greenhouse.io/company`.
2. Click **Add company**.
3. Click **Scrape** on the company card.
4. Filter jobs from the dashboard.
5. Use **Open application** or **Apply** to visit the original posting.

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

The `v2` branch is reserved for resume-aware matching, alerts, scheduled scraping, recruiter intelligence, and optional Gemini integration.
