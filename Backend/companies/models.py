from django.db import models
from django.utils import timezone


class Company(models.Model):
    PRIORITY_CHOICES = [
        ("dream", "Dream"),
        ("high", "High"),
        ("normal", "Normal"),
        ("fallback", "Fallback"),
    ]

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

    SOURCE_HEALTH_CHOICES = [
        ("needs_setup", "Needs setup"),
        ("needs_source", "Needs source"),
        ("needs_review", "Needs review"),
        ("active", "Active"),
        ("degraded", "Degraded"),
        ("failing", "Failing"),
        ("paused", "Paused"),
        ("blocked", "Blocked"),
    ]

    WORK_MODE_CHOICES = [
        ("any", "Any"),
        ("remote", "Remote"),
        ("hybrid", "Hybrid"),
        ("onsite", "Onsite"),
    ]

    DISCOVERY_STATUS_CHOICES = [
        ("not_started", "Not started"),
        ("queued", "Queued"),
        ("found", "Found"),
        ("needs_review", "Needs review"),
        ("failed", "Failed"),
        ("manual", "Manual"),
    ]

    name = models.CharField(max_length=180)
    domain = models.CharField(max_length=180, blank=True)
    homepage_url = models.URLField(blank=True)
    careers_url = models.URLField(blank=True, default="")
    priority_tier = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="normal")
    scraper_type = models.CharField(max_length=40, choices=SCRAPER_CHOICES, default="unknown")
    is_active = models.BooleanField(default=True)
    source_health = models.CharField(max_length=20, choices=SOURCE_HEALTH_CHOICES, default="needs_setup")
    source_discovery_status = models.CharField(
        max_length=20,
        choices=DISCOVERY_STATUS_CHOICES,
        default="not_started",
    )
    source_discovery_confidence = models.PositiveIntegerField(default=0)
    source_discovery_notes = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    title_keywords = models.JSONField(default=list, blank=True)
    negative_title_keywords = models.JSONField(default=list, blank=True)
    location_keywords = models.JSONField(default=list, blank=True)
    work_mode_filter = models.CharField(max_length=20, choices=WORK_MODE_CHOICES, default="any")
    scan_frequency_hours = models.PositiveIntegerField(default=24)
    alert_new_roles = models.BooleanField(default=True)
    last_scraped_at = models.DateTimeField(null=True, blank=True)
    last_scrape_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="never")
    last_scrape_message = models.TextField(blank=True)
    last_successful_scan_at = models.DateTimeField(null=True, blank=True)
    last_failed_scan_at = models.DateTimeField(null=True, blank=True)
    consecutive_failure_count = models.PositiveIntegerField(default=0)
    last_new_role_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "companies"
        constraints = [
            models.UniqueConstraint(fields=["domain"], condition=~models.Q(domain=""), name="unique_company_domain_when_present"),
            models.UniqueConstraint(fields=["careers_url"], condition=~models.Q(careers_url=""), name="unique_company_careers_url_when_present"),
        ]

    def __str__(self) -> str:
        return self.name

    def mark_scrape_result(self, status: str, message: str = "") -> None:
        now = timezone.now()
        self.last_scraped_at = now
        self.last_scrape_status = status
        self.last_scrape_message = message[:1000]
        update_fields = ["last_scraped_at", "last_scrape_status", "last_scrape_message", "updated_at"]
        if status == "success":
            self.last_successful_scan_at = now
            self.consecutive_failure_count = 0
            self.source_health = "active"
            update_fields.extend(["last_successful_scan_at", "consecutive_failure_count", "source_health"])
        elif status == "failed":
            self.last_failed_scan_at = now
            self.consecutive_failure_count += 1
            self.source_health = "failing" if self.consecutive_failure_count >= 3 else "degraded"
            update_fields.extend(["last_failed_scan_at", "consecutive_failure_count", "source_health"])
        self.save(update_fields=update_fields)

    @property
    def primary_source(self):
        return self.job_sources.filter(is_primary=True).order_by("-confidence_score", "id").first()


class CompanyJobSource(models.Model):
    SOURCE_TYPE_CHOICES = [
        ("careers", "Careers"),
        ("jobs", "Jobs"),
        ("ats", "ATS"),
        ("manual", "Manual"),
        ("unknown", "Unknown"),
    ]

    DISCOVERY_METHOD_CHOICES = [
        ("manual", "Manual"),
        ("csv", "CSV"),
        ("deterministic_agent", "Deterministic agent"),
        ("llm_agent", "LLM agent"),
    ]

    STATUS_CHOICES = [
        ("active", "Active"),
        ("needs_review", "Needs review"),
        ("failed", "Failed"),
        ("disabled", "Disabled"),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="job_sources")
    url = models.URLField(max_length=1000, unique=True)
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPE_CHOICES, default="careers")
    platform = models.CharField(max_length=40, default="unknown")
    discovery_method = models.CharField(max_length=40, choices=DISCOVERY_METHOD_CHOICES, default="deterministic_agent")
    confidence_score = models.PositiveIntegerField(default=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="needs_review")
    is_primary = models.BooleanField(default=False)
    evidence = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["company__name", "-is_primary", "-confidence_score", "url"]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["is_primary", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.company.name}: {self.url}"


class ScrapeLog(models.Model):
    STATUS_CHOICES = [
        ("running", "Running"),
        ("success", "Success"),
        ("failed", "Failed"),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="scrape_logs")
    source = models.ForeignKey(CompanyJobSource, on_delete=models.SET_NULL, null=True, blank=True, related_name="scrape_logs")
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


class ScanJob(models.Model):
    STATUS_CHOICES = [
        ("queued", "Queued"),
        ("running", "Running"),
        ("success", "Success"),
        ("partial_success", "Partial success"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
        ("skipped", "Skipped"),
    ]

    TRIGGER_CHOICES = [
        ("manual", "Manual"),
        ("scheduled", "Scheduled"),
        ("command", "Command"),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="scan_jobs")
    source = models.ForeignKey(CompanyJobSource, on_delete=models.SET_NULL, null=True, blank=True, related_name="crawl_runs")
    scrape_log = models.OneToOneField(ScrapeLog, on_delete=models.SET_NULL, null=True, blank=True, related_name="scan_job")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="queued")
    trigger = models.CharField(max_length=20, choices=TRIGGER_CHOICES, default="manual")
    source_platform = models.CharField(max_length=40, blank=True)
    message = models.TextField(blank=True)
    jobs_found = models.PositiveIntegerField(default=0)
    jobs_created = models.PositiveIntegerField(default=0)
    jobs_updated = models.PositiveIntegerField(default=0)
    alerts_created = models.PositiveIntegerField(default=0)
    requested_at = models.DateTimeField(default=timezone.now)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-requested_at", "-created_at"]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["status", "requested_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.company.name} scan {self.status}"


class JobAlert(models.Model):
    STATUS_CHOICES = [
        ("unread", "Unread"),
        ("read", "Read"),
        ("dismissed", "Dismissed"),
    ]

    ALERT_TYPE_CHOICES = [
        ("new_role", "New role"),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="job_alerts")
    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE, related_name="alerts")
    scan_job = models.ForeignKey(ScanJob, on_delete=models.SET_NULL, null=True, blank=True, related_name="alerts")
    alert_type = models.CharField(max_length=40, choices=ALERT_TYPE_CHOICES, default="new_role")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="unread")
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    dismissed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["company", "job", "alert_type"], name="unique_job_alert_per_company_job_type"),
        ]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["company", "status"]),
        ]

    def __str__(self) -> str:
        return self.title
