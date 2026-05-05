# Dogfood Baseline

Date: 2026-05-05

This is the first local dogfood baseline before the required one-week validation run.

## Setup

- Active tracked companies: 16.
- Candidate profile: present but empty.
- Stored jobs before scan: 0.
- Stored applications before scan: 0.
- Scan command: `python manage.py scan_due_companies --limit 16`.

## Scan Result

- Companies scanned: 16.
- Failed scans: 0.
- Skipped scans: 0.
- Alerts created: 867.
- Export created: `/tmp/job-scout-dogfood-export.json`.
- Export size: 5,375,790 bytes.

Jobs detected by company:

- Anthropic: 435.
- Notion: 142.
- Stripe: 137.
- Uber: 44.
- Apple: 30.
- Amazon: 19.
- Airbnb: 18.
- Cloudflare: 15.
- Databricks: 10.
- Google: 10.
- GitHub: 5.
- Netflix: 2.
- Microsoft: 0.
- Meta: 0.
- NVIDIA: 0.
- OpenAI: 0.

## Signal Quality Findings

- Source health was active across scanned companies.
- The empty profile made match scoring low-confidence and not useful enough for release judgement.
- Generic scraping imported some navigation-like entries such as Home, Teams, English, and Job Search.
- A generic parser false-positive filter and regression tests were added after this finding.
- The app needs dogfood with a real profile before match accuracy can be judged.

## Current Decision

This baseline proves the scanning loop can collect a large number of roles, but it also confirms the main product risk: adding more job noise is easy. Release judgement must depend on the one-week dogfood run with 25-50 companies, a real developer profile, feedback labels, and export/restore validation.

## Remaining Dogfood Work

- Add one real developer profile with accepted titles, skills, location preferences, and CV/profile markdown.
- Track 25-50 favorite companies.
- Run scheduled or manual scans for at least one week.
- Label alerts as relevant, maybe, or irrelevant.
- Check missed roles by manually comparing favorite company career pages.
- Verify export and restore before and after the run.
- Decide whether generic scraper coverage needs another source-specific adapter before deployment.
