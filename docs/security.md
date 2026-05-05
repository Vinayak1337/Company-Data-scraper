# Job Scout Security Baseline

Job Scout is built as a single-user personal application. The v2 deployed security baseline focuses on making a self-hosted instance harder to expose accidentally while keeping local setup simple.

## API Token Guard

Local development does not require an API token by default. For hosted deployments, set these backend variables:

```env
JOB_SCOUT_REQUIRE_AUTH=True
JOB_SCOUT_API_TOKEN=<long-random-token>
```

Then set the same token on the frontend service:

```env
BACKEND_API_TOKEN=<long-random-token>
```

The Next.js server-side API wrapper forwards the token to Django as a bearer token. `/api/health` remains public so Render and other hosts can run health checks.

## Careers URL Safety

Company watchlist URLs must use `http` or `https` and must point to a public hostname. Localhost, loopback, private IP ranges, link-local, multicast, reserved, and `.local` hostnames are rejected before scanning. This protects a deployed scraper from being used to probe local or private infrastructure.

## Current Limits

- This baseline is not a multi-user account system.
- Browser-visible frontend routes are not yet login-gated; the deployment expectation is a private instance plus the API token guard.
- Do not place provider API keys in the frontend environment. Keep AI and scraping secrets server-side only.
