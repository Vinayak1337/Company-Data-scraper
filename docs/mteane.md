# Optional MTEANE Event Automation

MTEANE is optional. Job Scout must work when it is disabled or unreachable.

## Purpose

Use MTEANE when the user wants rule-based notification delivery beyond Job Scout's local alerts, such as webhook, Slack, or email rules. Job Scout publishes safe events; MTEANE evaluates rules and runs actions.

## Source Layout

MTEANE should be linked as a git submodule at:

```text
integrations/mteane
```

The Docker Compose profile `mteane` expects that path to contain MTEANE's `Dockerfile.api` and `Dockerfile.worker`.

## Local Start

```bash
git submodule update --init --recursive
docker compose --profile mteane up --build
```

MTEANE's API is exposed locally on `http://127.0.0.1:3001`.
The MTEANE worker depends on the API health check so it starts after migrations complete.

Register an organization and save the returned API key:

```bash
curl -X POST http://127.0.0.1:3001/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Job Scout","slug":"job-scout"}'
```

Enable publishing from Job Scout:

```bash
MTEANE_ENABLED=True
MTEANE_API_URL=http://mteane-api:3000
MTEANE_API_KEY=<returned-api-key>
```

Use `http://127.0.0.1:3001` only from the host. Containers should call `http://mteane-api:3000`.

## Events

Job Scout only publishes safe, non-personal event payloads:

- `job.new_role`
- `scan.failed`
- `scan.recovered`
- `application.follow_up_due`
- `agent.run_failed`
- `weekly.generated`

Current implementation emits `job.new_role`, `scan.failed`, and `scan.recovered`.

Payloads must not include CV markdown, raw resume text, profile proof points, application notes, API keys, or secrets. The publisher redacts sensitive key names as a second line of defense.

## Failure Policy

- Disabled MTEANE is a no-op.
- Missing config is a no-op.
- Timeout or HTTP failure is logged and does not fail the originating scan or alert.
- MTEANE event delivery is not the source of truth; Job Scout's database remains authoritative.
