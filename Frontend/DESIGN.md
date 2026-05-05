# Job Scout Frontend Design Language

This document is the canonical design language for the Job Scout frontend. Keep it current when adding new routes, sections, states, or reusable components.

Job Scout is a repeated-use operating console for tracking companies, reviewing newly discovered roles, managing applications, maintaining profile context, and auditing AI-assisted workflows. The UI should feel calm, dense, precise, and trustworthy.

## Design Direction

- The default theme is the warm off-white operator workspace from the prototype, with a dark companion theme.
- The Company Tracker prototype is the interaction and composition reference: left workflow rail, compact top command/search, dense metric strips, list/detail screens, drawers, score bars, restrained badges, and operational tables.
- The frontend must not feel like a marketing site or public job board. Avoid hero sections, decorative card stacks, large empty illustrations, and generic gradient-heavy SaaS styling.
- Every section should answer an operational question: what changed, what needs review, what is healthy, what should the user do next?

## Tokens

Use semantic CSS variables, not route-specific colors. New components should consume these tokens through Tailwind arbitrary values or shared component classes.

### Dark Theme

- `--bg`: `#15140f`, main canvas.
- `--bg-raised`: `#1d1c17`, standard panels.
- `--bg-sunken`: `#100f0b`, inputs, code, and empty states.
- `--bg-hover`: `#25241e`, hover surfaces.
- `--bg-active`: `#2d2c25`, selected rows.
- `--ink`: `#f5f1e8`, primary text.
- `--ink-2`: `#d6d0c2`, secondary text.
- `--ink-3`: `#8a8377`, metadata text.
- `--ink-4`: `#4f4a3f`, disabled/quiet text.
- `--line`: `#2a2822`, low contrast structure.
- `--line-strong`: `#3a372f`, active controls and important separators.
- `--accent`: `#8aa6e0`, primary action accent.
- `--accent-soft`: `#1f2740`, selected/active background.
- `--accent-ink`: `#b8c8ed`, accent text.
- `--ok`: `#7fc09b`, healthy/success states.
- `--ok-soft`: `#1d2b22`, success badge surface.
- `--warn`: `#d6a45c`, review/stale/noisy states.
- `--warn-soft`: `#2e2418`, warning badge surface.
- `--danger`: `#d68080`, destructive/error states.
- `--danger-soft`: `#2e1e1e`, danger badge surface.

### Light Theme

- `--bg`: `#faf8f4`, warm canvas.
- `--bg-raised`: `#ffffff`, standard panels.
- `--bg-sunken`: `#f3f0ea`, inputs, code, and empty states.
- `--bg-hover`: `#f0ece4`, hover surfaces.
- `--bg-active`: `#e8e3d8`, selected rows.
- `--ink`: `#1a1815`, primary text.
- `--ink-2`: `#4a463f`, secondary text.
- `--ink-3`: `#807a6f`, metadata text.
- `--ink-4`: `#b5ae9f`, disabled/quiet text.
- `--line`: `#e8e3d8`, low contrast structure.
- `--line-strong`: `#d8d2c2`, active controls and important separators.
- `--accent`: `#3b5fa8`, primary action accent.
- `--accent-soft`: `#e8edf6`, selected/active background.
- `--accent-ink`: `#2a4884`, accent text.
- `--ok`: `#2d6a4f`, healthy/success states.
- `--ok-soft`: `#e3eee6`, success badge surface.
- `--warn`: `#a86a1f`, review/stale/noisy states.
- `--warn-soft`: `#f5ebd9`, warning badge surface.
- `--danger`: `#9b2f2f`, destructive/error states.
- `--danger-soft`: `#f3e0de`, danger badge surface.

## Typography

- Use Inter for most UI and long-form reading.
- Use Source Serif 4 for brand text, page titles, and metric numbers.
- Use JetBrains Mono for machine states, IDs, timestamps, metric labels, shortcut hints, commands, and scores.
- Page titles are editorial and serif-led, generally `42px` desktop and `32px` mobile.
- Labels use uppercase mono with letter spacing around `0.08em` to `0.14em`.
- Use tabular numbers for metrics, scores, counts, dates, and costs.

## Layout

- Desktop shell: fixed `232px` left sidebar, sticky top command bar, full-height content.
- Mobile shell: compact top header plus horizontally scrollable route nav.
- Main content should use a responsive max width around `1540px`; table/detail workflows may consume full width inside that boundary.
- Prefer list/detail layouts for review workflows. The left side preserves context; the right side exposes selected details and actions.
- Use drawers or sticky detail panes for selected records. Use modals only for short confirmation and destructive decisions.
- Do not put cards inside cards. Repeated records may be cards; page sections should be panels or unframed layout groups.

## Components

- `AppShell`: owns navigation, brand, mobile nav, top command/search, global status, and theme toggle.
- `PageHeader`: compact route title, operational description, and route-level actions.
- `PageSection`: standard section header, description, action slot, and panel body.
- `MetricCard`: label, value, optional detail/trend; value must use tabular numbers.
- `StatusBadge`: semantic badge for health, priority, workflow, provider, and source states.
- `Button`: icon-first where possible; use primary only for the main action in a section.
- `DataTable`: horizontal separators, compact rows, selected state, hover state, no vertical grid clutter.
- `DetailDrawer`: sticky desktop detail pane, normal-flow/mobile full-width panel, optional footer.
- `Tabs`: long-lived content groups such as Profile, Settings, drawers, and agent details.
- `SystemBanner`: compact success/info/warning/error notices with actionable recovery copy where possible.
- `CommandPalette`: global command/search surface for navigation and common actions.

## Route Patterns

- Today: backend state, metric strip, scan control, merged triage inbox, selected detail, recent scans.
- Companies: compact add company section, watchlist table, source health, filters, selected company detail, scan history.
- Jobs: compact filters, score-ranked role list, match/evidence detail, manual URL inbox.
- Applications: dense pipeline lanes and selected application detail.
- Profile: tabbed profile workspace plus readiness/status rail.
- Agents: runtime/provider status, run history, approval queue, selected run audit detail.
- Analytics: signal metrics, feedback queue, source quality, weekly review.
- Settings: health, notifications, integrations, ownership, and danger zone.

## Interaction Rules

- Selected records must be linkable through URL search params.
- Long text must truncate or wrap cleanly; never allow overflow in buttons, badges, tables, or drawer headers.
- Backend-down and source-failure states should be visible and actionable.
- Destructive actions belong in danger sections with explicit confirmation where the backend supports it.
- AI-generated claims and agent actions require clear review/consent states.
- Future features should extend shared components and route sections. Do not add one-off styling unless a new reusable pattern is being introduced.

## Verification

Before shipping a redesign change, run:

```bash
npm run lint
npm run build
npm run test:interactions
npm run test:a11y
```

Also verify both themes, desktop/mobile shell behavior, drawer layouts, keyboard focus, and text overflow.
