from django.db import models
from django.utils import timezone


class ManualUrlInboxItem(models.Model):
    ITEM_TYPE_CHOICES = [
        ("unknown", "Unknown"),
        ("company", "Company"),
        ("job", "Job"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("imported", "Imported"),
        ("dismissed", "Dismissed"),
    ]

    url = models.URLField(max_length=1000, unique=True)
    item_type = models.CharField(max_length=20, choices=ITEM_TYPE_CHOICES, default="unknown")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    title = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    inferred_company = models.CharField(max_length=180, blank=True)
    company = models.ForeignKey("companies.Company", on_delete=models.SET_NULL, null=True, blank=True, related_name="manual_inbox_items")
    job = models.ForeignKey("jobs.Job", on_delete=models.SET_NULL, null=True, blank=True, related_name="manual_inbox_items")
    imported_at = models.DateTimeField(null=True, blank=True)
    dismissed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["status", "-created_at"]
        indexes = [
            models.Index(fields=["status", "item_type", "created_at"]),
        ]

    def __str__(self) -> str:
        return self.title or self.url

    def mark_imported(self, company=None, job=None) -> None:
        self.status = "imported"
        self.company = company or self.company
        self.job = job or self.job
        self.imported_at = timezone.now()
        self.save(update_fields=["status", "company", "job", "imported_at", "updated_at"])

    def dismiss(self) -> None:
        self.status = "dismissed"
        self.dismissed_at = timezone.now()
        self.save(update_fields=["status", "dismissed_at", "updated_at"])
