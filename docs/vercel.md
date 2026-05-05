# Vercel Frontend Deployment

The preferred split deployment is Vercel for `Frontend/` and a Docker/VPS or Render backend for the Django API.

## Project Settings

- Framework preset: Next.js.
- Root directory: `Frontend`.
- Build command: `npm run build`.
- Install command: `npm ci`.
- Output: Next.js default.

## Environment

Set these Vercel environment variables:

```bash
BACKEND_API_BASE_URL=https://api.example.com/api
BACKEND_API_TOKEN=<same-value-as-JOB_SCOUT_API_TOKEN-if-auth-is-enabled>
NEXT_TELEMETRY_DISABLED=1
```

`BACKEND_API_TOKEN` is server-side only. Do not expose it with a `NEXT_PUBLIC_` prefix.

The value must exactly match the backend `JOB_SCOUT_API_TOKEN`. A mismatch makes the frontend render backend authorization errors.

## Backend Requirements

The backend must allow the Vercel domain:

```bash
ALLOWED_HOSTS=api.example.com
CSRF_TRUSTED_ORIGINS=https://app.example.com,https://*.vercel.app
JOB_SCOUT_REQUIRE_AUTH=True
JOB_SCOUT_API_TOKEN=<generated-api-token>
```

## Smoke Test

After deployment:

```bash
BACKEND_URL=https://api.example.com/api FRONTEND_URL=https://app.example.com BACKEND_API_TOKEN=<generated-api-token> ./scripts/smoke-test.sh
```

Any backend `500`, frontend route failure, or auth mismatch blocks release.
