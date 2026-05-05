# Optional P2 Integrations

These integrations are opt-in. None of them should block the core local watchlist workflow.

## Bookmarklet

`scripts/job-scout-bookmarklet.js` saves the current browser URL into `/api/discovery/inbox`.

Use it only after the backend is reachable from the browser. It does not read private page content beyond URL, title, and user-entered notes.

## Browser Extension Evaluation

Do not build an extension until the bookmarklet fails a real workflow. Extension scope must stay limited to:

- Current tab URL/title capture.
- User-confirmed content capture.
- No background scraping.
- No credential/session extraction.

## Webhook, Discord, Slack

Notification integrations may be added after local/email notifications are reliable. Required controls:

- Disabled by default.
- User-owned webhook URL stored only in local env/settings.
- Quiet hours and digest settings apply.
- No CV/profile text in outbound payloads.

## GitHub/Portfolio Import

Advanced portfolio import is P2. It must:

- Read only public repositories or user-provided exports.
- Convert projects into unconfirmed proof points.
- Require user confirmation before profile/CV use.

## Compensation Research

Automation is allowed only with source labels and manual review:

- Store source URL, capture date, geography, level, and caveats.
- Never present a single salary number as truth.
- Keep offer comparison manual-first.

## Tech-Stack Catalogs

Tech-stack company catalogs can seed watchlists, but must be editable and source-labeled. Catalog import should never replace the user's favorite-company list.
