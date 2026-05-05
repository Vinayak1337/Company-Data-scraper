# Deployment Readiness

This is the remaining work needed before treating v2 as deployment-ready.

## Current Target

- Frontend: Vercel, rooted at `Frontend/`.
- Backend stack: Docker Compose for local/VPS, with Django web, Postgres, scanner, and agent worker.
- Render: still supported through `render.yaml`, but production Render should use separate services/workers rather than one multi-process web service.
- MTEANE: optional submodule/service profile for event automation.

## Readiness Waves

### Wave 29: Stabilize Current V2

- Verify the scraper false-positive filter with tests and dogfood fixtures.
- Document dogfood scan results, source-quality issues, empty-profile limitations, and cleanup actions.
- Keep new core product features frozen until deploy smoke passes.

### Wave 30: Docker/VPS Deployment

- Maintain `Backend/Dockerfile` and root `docker-compose.yml`.
- Confirm Django web, scanner, and agent worker can restart independently.
- Document VPS reverse proxy, env vars, backups, and smoke testing.

### Wave 31: Vercel Frontend Deployment

- Keep `Frontend/.env.example` and `docs/vercel.md` aligned.
- Confirm Vercel server-side API calls work with `BACKEND_API_BASE_URL` and `BACKEND_API_TOKEN`.
- Smoke test Vercel frontend against the deployed backend.

### Wave 32: Optional MTEANE Service

- Link MTEANE at `integrations/mteane` as a submodule.
- Keep MTEANE behind the Compose `mteane` profile.
- Publish only safe events and never block Job Scout workflows on MTEANE delivery.
- Ensure the MTEANE worker starts only after API health confirms migrations have completed.

### Wave 33: Release Operations

- Require API-token auth for deployed personal instances.
- Verify export and restore before and after dogfood, including redacted agent run history.
- Run one-week dogfood with 25-50 companies and one real developer profile.
- Review source health, missed roles, noisy alerts, match accuracy, and restore/export reliability.
- Stage and commit the v2 work in logical groups after the verification gates pass.

### Wave 34: Durable Agentic Workflow Boundary

- Keep LangSmith as optional tracing and evaluation support.
- Keep LangChain out of the core until a concrete adapter requires it.
- Defer LangGraph until workflows need durable branching, waiting, replay, or resumable state machines.
- Candidate LangGraph workflows: company watch, profile-to-role matching, application prep, and weekly learning.

## Backlog Control

- P1: real hosted AI adapter execution beyond deterministic local adapters.
- P1: deeper scraper/source coverage if dogfood exposes repeated gaps.
- P2: browser extension, Slack/Discord/webhooks, GitHub/portfolio import, compensation automation, and richer tech-stack catalogs.
