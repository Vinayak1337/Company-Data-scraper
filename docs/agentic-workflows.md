# Agentic Workflow Contracts

Job Scout agents are review assistants, not autonomous job appliers. Django remains the control plane for state, permissions, artifacts, audit logs, approvals, and user-facing results.

## Current Release

The first release uses Django `AgentRun` records with deterministic local adapters and optional LangSmith tracing. LangChain is not required. LangGraph is not required.

## Workflow 1: Company Watch

Purpose: reduce missed favorite-company roles without increasing job-board noise.

Steps:

1. Scan due tracked companies.
2. Normalize jobs and dedupe by company/apply URL.
3. Classify new roles as relevant, maybe, duplicate, noisy, or blocked.
4. Score against the profile and search strategy.
5. Create alerts or digest entries with evidence and caveats.
6. Wait for user feedback labels.
7. Propose filter/source-health changes, but do not apply them without approval.

LangGraph trigger: use only if role classification, retry, user feedback wait states, and source-health remediation become a branching state machine.

## Workflow 2: Profile-To-Role Match

Purpose: explain why a role is or is not worth applying to.

Steps:

1. Snapshot the active profile, target titles, skills, proof points, and search strategy.
2. Score roles using deterministic matching first.
3. Use AI only for ambiguous job descriptions, gap explanations, and title synonym expansion.
4. Return evidence, missing skills, confidence, and apply priority.
5. Capture corrections and update learning proposals.

LangGraph trigger: use only if matching requires durable multi-pass review, user correction waits, or replayable evaluation branches.

## Workflow 3: Application Prep

Purpose: help users prepare stronger applications after they choose a role.

Steps:

1. Snapshot job, company, profile, proof points, and existing application state.
2. Generate CV tailoring notes, cover note, recruiter message, and answer-bank draft.
3. Mark all outputs as drafts.
4. Ask the user to approve, edit, or reject each artifact.
5. Save only approved artifacts.

LangGraph trigger: use only if prep becomes a long-running workflow with multiple approval gates, document generation retries, and resumable user edits.

## Workflow 4: Weekly Learning

Purpose: make the tracker better from real user feedback.

Steps:

1. Summarize scans, alerts, applications, missed roles, source failures, and feedback.
2. Identify noisy companies, titles, locations, and source types.
3. Propose watchlist/filter/search-strategy changes.
4. Require approval before applying changes.
5. Store weekly review and learning-change records with undo support.

LangGraph trigger: use only if weekly learning needs durable branching between evidence review, proposal generation, approval, undo, and re-evaluation.

## LangSmith

LangSmith may be used to inspect AI-produced responses and traces when enabled:

```env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=<langsmith-api-key>
LANGSMITH_PROJECT=job-scout-v2
```

Traces must use redacted inputs. Local audit logs remain authoritative.
