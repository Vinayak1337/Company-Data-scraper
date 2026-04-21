from django.db import models
from django.utils import timezone


class Company(models.Model):
    SCRAPER_CHOICES = [
        ("greenhouse", "Greenhouse"),
        ("lever", "Lever"),
        ("ashby", "Ashby"),
        ("microsoft", "Microsoft Careers"),
        ("generic", "Generic HTML"),
        ("unknown", "Unknown"),
    ]

    STATUS_CHOICES = [
        ("never", "Never scraped"),
        ("success", "Success"),
        ("failed", "Failed"),
    ]

    name = models.CharField(max_length=180)
    careers_url = models.URLField(unique=True)
    scraper_type = models.CharField(max_length=40, choices=SCRAPER_CHOICES, default="unknown")
    is_active = models.BooleanField(default=True)
    last_scraped_at = models.DateTimeField(null=True, blank=True)
    last_scrape_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="never")
    last_scrape_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "companies"

    def __str__(self) -> str:
        return self.name

    def mark_scrape_result(self, status: str, message: str = "") -> None:
        self.last_scraped_at = timezone.now()
        self.last_scrape_status = status
        self.last_scrape_message = message[:1000]
        self.save(update_fields=["last_scraped_at", "last_scrape_status", "last_scrape_message", "updated_at"])


class ScrapeLog(models.Model):
    STATUS_CHOICES = [
        ("running", "Running"),
        ("success", "Success"),
        ("failed", "Failed"),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="scrape_logs")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="running")
    source_platform = models.CharField(max_length=40, blank=True)
    jobs_found = models.PositiveIntegerField(default=0)
    jobs_created = models.PositiveIntegerField(default=0)
    jobs_updated = models.PositiveIntegerField(default=0)
    message = models.TextField(blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def finish(self, status: str, message: str = "", jobs_found: int = 0, jobs_created: int = 0, jobs_updated: int = 0) -> None:
        self.status = status
        self.message = message[:2000]
        self.jobs_found = jobs_found
        self.jobs_created = jobs_created
        self.jobs_updated = jobs_updated
        self.finished_at = timezone.now()
        self.save()
