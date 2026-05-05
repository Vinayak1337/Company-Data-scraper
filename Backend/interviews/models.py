from django.db import models


class InterviewPrep(models.Model):
    STAGE_CHOICES = [
        ("screen", "Screen"),
        ("technical", "Technical"),
        ("onsite", "Onsite"),
        ("final", "Final"),
        ("unknown", "Unknown"),
    ]

    application = models.OneToOneField("applications.Application", on_delete=models.CASCADE, related_name="interview_prep")
    stage = models.CharField(max_length=40, choices=STAGE_CHOICES, default="unknown")
    checklist = models.JSONField(default=list, blank=True)
    focus_areas = models.JSONField(default=list, blank=True)
    question_bank = models.JSONField(default=list, blank=True)
    story_bank = models.JSONField(default=list, blank=True)
    gaps = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True)
    generated_by = models.CharField(max_length=80, default="deterministic")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"Interview prep for {self.application}"


class OfferSupport(models.Model):
    application = models.OneToOneField("applications.Application", on_delete=models.CASCADE, related_name="offer_support")
    offer_stage = models.CharField(max_length=80, blank=True)
    base_salary_min = models.PositiveIntegerField(null=True, blank=True)
    base_salary_max = models.PositiveIntegerField(null=True, blank=True)
    equity_notes = models.TextField(blank=True)
    benefits_notes = models.TextField(blank=True)
    manual_research = models.JSONField(default=list, blank=True)
    decision_criteria = models.JSONField(default=list, blank=True)
    negotiation_points = models.JSONField(default=list, blank=True)
    compensation_notes = models.TextField(blank=True)
    risk_flags = models.JSONField(default=list, blank=True)
    generated_by = models.CharField(max_length=80, default="deterministic")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"Offer support for {self.application}"
