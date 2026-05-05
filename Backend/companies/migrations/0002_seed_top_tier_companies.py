from django.db import migrations, models


TOP_TIER_COMPANIES = [
    ("Microsoft", "https://apply.careers.microsoft.com/careers?start=0&sort_by=relevance&filter_include_remote=1", "microsoft"),
    ("OpenAI", "https://jobs.ashbyhq.com/OpenAI", "ashby"),
    ("Anthropic", "https://job-boards.greenhouse.io/anthropic", "greenhouse"),
    ("Stripe", "https://stripe.com/jobs/search", "generic"),
    ("Google", "https://www.google.com/about/careers/applications/jobs/results", "generic"),
    ("Amazon", "https://www.amazon.jobs/en/search", "generic"),
    ("Apple", "https://jobs.apple.com/en-us/search", "generic"),
    ("Meta", "https://www.metacareers.com/jobs", "generic"),
    ("NVIDIA", "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite", "generic"),
    ("Netflix", "https://explore.jobs.netflix.net/careers", "generic"),
    ("Uber", "https://www.uber.com/us/en/careers/list/", "generic"),
    ("Airbnb", "https://careers.airbnb.com/positions/", "generic"),
    ("Databricks", "https://www.databricks.com/company/careers/open-positions", "generic"),
    ("Notion", "https://www.notion.com/careers", "generic"),
    ("Cloudflare", "https://www.cloudflare.com/careers/jobs/", "generic"),
    ("GitHub", "https://www.github.careers/careers-home/jobs", "generic"),
]


def seed_companies(apps, schema_editor):
    Company = apps.get_model("companies", "Company")
    for name, careers_url, scraper_type in TOP_TIER_COMPANIES:
        Company.objects.get_or_create(
            careers_url=careers_url,
            defaults={"name": name, "scraper_type": scraper_type, "is_active": True},
        )


class Migration(migrations.Migration):
    dependencies = [
        ("companies", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="company",
            name="scraper_type",
            field=models.CharField(choices=[("greenhouse", "Greenhouse"), ("lever", "Lever"), ("ashby", "Ashby"), ("microsoft", "Microsoft Careers"), ("generic", "Generic HTML"), ("unknown", "Unknown")], default="unknown", max_length=40),
        ),
        migrations.RunPython(seed_companies, migrations.RunPython.noop),
    ]
