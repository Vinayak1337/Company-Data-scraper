# AI Runtime Operations

Job Scout keeps agent execution reviewable and bounded. Agent runs record provider, model, tool policy, permissions, runtime invocations, artifacts, and audit logs.

## Execution Modes

Local development uses inline execution by default:

```env
AGENT_EXECUTION_MODE=inline
```

For hosted deployments, use queued execution and run a worker process:

```env
AGENT_EXECUTION_MODE=queued
AGENT_QUEUE_BATCH_SIZE=5
```

Worker command:

```bash
python manage.py process_agent_queue --limit 5
```

## Consent And Budgets

Each provider can require explicit user consent before a run starts. Providers also expose:

- Daily run limit
- Monthly budget in cents
- Estimated cost per run in cents
- Worker-only flag for CLI adapters

The app blocks runs when consent is missing, the daily limit is exhausted, or the projected monthly spend exceeds the configured budget.

## CLI Adapters

Gemini CLI, Claude Code CLI, and OpenCode are represented as worker-only adapters. They are intentionally blocked in web requests. Future worker implementation must keep the same audit, permission, and artifact model before executing CLI commands.

## Optional LangSmith Tracing

LangSmith is optional and framework-agnostic in Job Scout. It is used for AI observability only; LangChain is not required for the current orchestrator.

```env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=<langsmith-api-key>
LANGSMITH_PROJECT=job-scout-v2
```

When enabled, agent executions are traced with redacted inputs, provider/model metadata, tool policy, prompt version, and output status. The Django audit log stores the LangSmith trace ID so a local `AgentRun` can be matched to the external trace. Agent runs still work when LangSmith is disabled, the SDK is unavailable, or tracing fails.

Do not send raw resumes, CV markdown, profile markdown, secret env values, private notes, or untrusted scraper payloads to LangSmith unless the user has explicitly opted into that data exposure.

## LangGraph Decision Boundary

Do not adopt LangGraph for the first production agent slice. Django already owns run state, permissions, artifacts, audit logs, approval gates, and queue dispatch.

LangGraph becomes useful later only for durable workflows with branching, waiting, and resume semantics, such as:

- Company Watch Workflow: scan source, classify roles, dedupe/noise check, match profile, create alert or digest.
- Profile-to-Role Match Workflow: update profile snapshot, score jobs, explain gaps, wait for user feedback, adjust strategy.
- Application Prep Workflow: prepare CV notes, cover note, recruiter message, answer bank, wait for approval before saving artifacts.
- Weekly Learning Workflow: summarize feedback, propose filter/title changes, wait for approval, apply accepted preferences.

If LangGraph is added, it must sit behind the Django Agent Orchestrator as an execution engine. It must not bypass tool policy, approval gates, audit logging, redaction, budgets, or user-facing artifact storage.

See `docs/agentic-workflows.md` for the workflow contracts and LangGraph trigger criteria.
