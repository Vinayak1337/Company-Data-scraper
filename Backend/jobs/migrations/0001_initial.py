from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("companies", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Job",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("location", models.CharField(blank=True, max_length=255)),
                ("description", models.TextField(blank=True)),
                ("apply_url", models.URLField(max_length=1000)),
                ("source_url", models.URLField(max_length=1000)),
                ("source_platform", models.CharField(max_length=40)),
                ("external_id", models.CharField(blank=True, max_length=255)),
                ("posted_at", models.DateTimeField(blank=True, null=True)),
                ("tags", models.JSONField(blank=True, default=list)),
                ("remote_policy", models.CharField(choices=[("unknown", "Unknown"), ("remote", "Remote"), ("hybrid", "Hybrid"), ("onsite", "Onsite")], default="unknown", max_length=20)),
                ("first_seen_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("last_seen_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="jobs", to="companies.company")),
            ],
            options={"ordering": ["-posted_at", "-first_seen_at", "title"], "constraints": [models.UniqueConstraint(fields=("company", "apply_url"), name="unique_job_apply_url_per_company")]},
        ),
    ]
