# V2 Release Audit

## Acceptance Summary

- Company watchlist, source health, scan cadence, pause/resume, filters, manual rescans: implemented.
- Today queue, alerts, application tracker, follow-ups: implemented.
- Profile Studio, resume import, target titles, proof points, search strategy: implemented.
- Match intelligence with evidence, corrections, and undoable learning changes: implemented.
- Agent orchestrator, providers, runtime policy, artifacts, decisions, audit logs: implemented.
- Company/recruiter intelligence, interview prep, offer support: implemented with public-source/manual-first constraints.
- Export, full restore, delete-all-personal-data, redaction audit: implemented.
- Render split deployment, smoke script, CI quality gates: implemented.

## Explicit Deferrals

- Real hosted AI adapter execution beyond deterministic local adapters remains P1.
- Browser extension remains P2 until bookmarklet usage proves insufficient.
- Slack/Discord/webhooks remain P2 until local/email notification reliability is proven.
- Advanced GitHub/portfolio import remains P2 and must create unconfirmed proof points only.
- Compensation automation remains P2 with strict source labeling.
- Multi-user workspace, social features, autonomous outreach, and auto-apply remain rejected.

## Dogfood Plan

Baseline local dogfood notes are captured in [dogfood-baseline.md](dogfood-baseline.md). That baseline is not a substitute for the required one-week validation.

Run one disposable or backed-up workspace with:

- 25-50 favorite companies.
- One real developer profile.
- At least one week of scheduled or manual scans.
- Alert feedback labels: relevant, maybe, irrelevant.
- Five saved applications from tracked-company alerts where possible.

Pass criteria:

- The app catches at least one role the user would otherwise manually check later.
- Source health makes failed tracking obvious.
- Strong-fit jobs show evidence the user agrees with.
- Feedback reduces noisy alerts or generates useful filter suggestions.
- Export and restore work before/after dogfood.

## Manual Job-Board Comparison

Compare against current manual process:

- Time spent checking favorite companies.
- Missed or late-discovered roles.
- Alert relevance.
- Effort to decide whether to apply.
- Effort to prepare application material.

The app is worth continuing only if it reduces missed favorite-company roles or improves application quality without adding equivalent review burden.
