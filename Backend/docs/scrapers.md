# Scraper Plugins

Scrapers live in `scrapers_engine/`.

Each adapter returns normalized jobs using:

```python
NormalizedJob(
    title="Backend Engineer",
    company_name="Acme",
    location="Remote",
    description="...",
    apply_url="https://...",
    source_url="https://...",
    source_platform="lever",
    external_id="optional",
    tags=["python", "django"],
    remote_policy="remote",
)
```

To add a scraper:

1. Create a class in `scrapers_engine/adapters.py`.
2. Implement `can_handle(url)` and `scrape(url)`.
3. Add the class instance to `SCRAPERS`.
4. Add tests in `scrapers_engine/tests.py`.

Keep adapters deterministic in v1. Do not add AI parsing to this branch.

Microsoft Careers pages are handled through `application/ld+json` `JobPosting` data. A Microsoft search URL without a selected job may expose no job postings to static HTML; a URL containing `pid=...` is the most reliable input for that adapter.
