from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Company",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=180)),
                ("careers_url", models.URLField(unique=True)),
                ("scraper_type", models.CharField(choices=[("greenhouse", "Greenhouse"), ("lever", "Lever"), ("ashby", "Ashby"), ("generic", "Generic HTML"), ("unknown", "Unknown")], default="unknown", max_length=40)),
                ("is_active", models.BooleanField(default=True)),
                ("last_scraped_at", models.DateTimeField(blank=True, null=True)),
                ("last_scrape_status", models.CharField(choices=[("never", "Never scraped"), ("success", "Success"), ("failed", "Failed")], default="never", max_length=20)),
                ("last_scrape_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["name"], "verbose_name_plural": "companies"},
        ),
        migrations.CreateModel(
            name="ScrapeLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("running", "Running"), ("success", "Success"), ("failed", "Failed")], default="running", max_length=20)),
                ("source_platform", models.CharField(blank=True, max_length=40)),
                ("jobs_found", models.PositiveIntegerField(default=0)),
                ("jobs_created", models.PositiveIntegerField(default=0)),
                ("jobs_updated", models.PositiveIntegerField(default=0)),
                ("message", models.TextField(blank=True)),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="scrape_logs", to="companies.company")),
            ],
            options={"ordering": ["-started_at"]},
        ),
    ]
