from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone

from companies.models import Company
from jobs.models import Job
from matching.models import JobMatch
from notifications.models import NotificationPreference
from notifications.services import (
    create_notification_event,
    notification_preferences_status,
    send_queued_notification_events,
)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class NotificationEmailTests(TestCase):
    def setUp(self):
        mail.outbox = []

    def test_immediate_match_notification_sends_email(self):
        match = self.create_match()
        NotificationPreference.objects.create(
            digest_channel="email",
            email_address="user@example.com",
            immediate_email_enabled=True,
            digest_enabled=True,
        )

        event = create_notification_event(match)

        self.assertEqual(event.channel, "email")
        self.assertEqual(event.status, "sent")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("85% match", mail.outbox[0].subject)
        self.assertIn(match.job.apply_url, mail.outbox[0].body)

    def test_email_without_address_is_skipped(self):
        match = self.create_match()
        NotificationPreference.objects.create(
            digest_channel="email",
            immediate_email_enabled=True,
            digest_enabled=True,
        )

        event = create_notification_event(match)

        self.assertEqual(event.status, "skipped")
        self.assertEqual(event.skipped_reason, "No notification email address is configured.")
        self.assertEqual(len(mail.outbox), 0)

    def test_quiet_hours_keeps_email_queued(self):
        match = self.create_match()
        NotificationPreference.objects.create(
            digest_channel="email",
            email_address="user@example.com",
            immediate_email_enabled=True,
            quiet_hours_enabled=True,
            quiet_hours_start=timezone.localtime().time().replace(second=0, microsecond=0),
            quiet_hours_end=timezone.localtime().time().replace(second=0, microsecond=0),
        )

        event = create_notification_event(match)

        self.assertEqual(event.status, "queued")
        self.assertIn("Quiet hours", event.skipped_reason)
        self.assertEqual(len(mail.outbox), 0)

    def test_send_queued_notification_events_sends_pending_email(self):
        match = self.create_match()
        NotificationPreference.objects.create(
            digest_channel="email",
            email_address="user@example.com",
            immediate_email_enabled=False,
            digest_enabled=True,
        )
        event = create_notification_event(match)
        self.assertEqual(event.status, "queued")

        result = send_queued_notification_events(limit=5)

        event.refresh_from_db()
        self.assertEqual(result["sent"], 1)
        self.assertEqual(event.status, "sent")
        self.assertEqual(len(mail.outbox), 1)

    def test_notification_status_requires_delivery_channel(self):
        preference = NotificationPreference.objects.create(digest_enabled=True, digest_channel="email")
        self.assertFalse(notification_preferences_status(preference)["configured"])

        preference.email_address = "user@example.com"
        preference.save(update_fields=["email_address"])

        self.assertTrue(notification_preferences_status(preference)["configured"])

    def create_match(self) -> JobMatch:
        company = Company.objects.create(name="Acme", domain="acme.test", careers_url="https://acme.test/jobs")
        job = Job.objects.create(
            company=company,
            title="Backend Engineer",
            description="Python and Django role.",
            location="Remote",
            apply_url="https://acme.test/jobs/backend",
            source_url="https://acme.test/jobs",
            source_platform="generic",
            first_seen_at=timezone.now(),
        )
        return JobMatch.objects.create(
            job=job,
            overall_score=85,
            confidence_score=77,
            apply_priority="apply_now",
            should_notify=True,
            reasons_to_apply=["Python and Django match the profile."],
            reasons_to_skip=["Compensation not listed."],
        )
