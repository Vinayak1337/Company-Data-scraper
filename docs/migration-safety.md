# Migration Safety

Before risky schema or data migrations, create an export and a database backup.

## Required Preflight

1. Run backend checks:

```bash
cd Backend
../.venv/bin/python manage.py makemigrations --check --dry-run
../.venv/bin/python manage.py check
../.venv/bin/python manage.py test
```

2. Export the workspace:

```bash
curl -fsS http://127.0.0.1:8000/api/export > job-scout-export.json
```

3. For Render/Postgres, create a provider-level backup or point-in-time restore marker before applying migrations.

## Risk Markers

Treat these changes as risky:

- Dropping tables or columns.
- Renaming models, fields, or apps.
- Adding non-null fields without safe defaults.
- Changing URL uniqueness, job dedupe keys, or application relationships.
- Migrating profile, CV, AI prompt, artifact, or application text.
- Bulk rewriting scan history or match scores.

## Rollback Preference

Prefer restoring a database backup for failed schema migrations. Use `POST /api/import/workspace` only for user-owned data restore into a compatible schema.
