# Deploying Job Scout v1 on Render

## Option 1: Blueprint

1. Push the repository to GitHub.
2. In Render, choose **New > Blueprint**.
3. Select the repo.
4. Render reads `render.yaml` and creates:
   - Django web service
   - PostgreSQL database
5. Deploy.

## Option 2: Manual Web Service

Create a Render PostgreSQL database, then create a Web Service with:

- Runtime: Python
- Build command: `./build.sh`
- Start command: `gunicorn jobhunt.wsgi:application`

Set environment variables:

- `SECRET_KEY`
- `DATABASE_URL`
- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`
- `PYTHON_VERSION=3.13.5`

For a Render URL like `https://job-scout.onrender.com`, use:

```text
ALLOWED_HOSTS=job-scout.onrender.com
CSRF_TRUSTED_ORIGINS=https://job-scout.onrender.com
```

## Health Check

Use:

```text
/api/health
```

The endpoint returns:

```json
{"status": "ok"}
```

## UptimeRobot

Create an HTTP monitor pointing at:

```text
https://your-render-service.onrender.com/api/health
```

This keeps the service warm enough for manual use on Render's free plan.

## Notes

- V1 scraping is manual from the UI.
- Scheduled scraping belongs in v2, preferably via Render Cron Jobs or a Django management command.
- Some websites block scraping. ATS URLs such as Lever and Greenhouse are the most reliable targets.
