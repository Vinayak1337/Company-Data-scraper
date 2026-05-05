from unittest.mock import patch

import requests
from django.test import TestCase, override_settings
from django.utils import timezone

from companies.models import Company, ScanJob
from companies.services import create_new_role_alerts
from jobs.models import Job
from notifications.mteane import publish_mteane_event, redact_payload


class MteaneIntegrationTests(TestCase):
    @patch("notifications.mteane.requests.post")
    def test_mteane_disabled_is_noop(self, mock_post):
        result = publish_mteane_event("job.new_role", {"job_title": "Engineer"})

        self.assertFalse(result.delivered)
        self.assertEqual(result.status, "disabled")
        mock_post.assert_not_called()

    @override_settings(MTEANE_ENABLED=True, MTEANE_API_URL="http://mteane:3000", MTEANE_API_KEY="test-key")
    @patch("notifications.mteane.requests.post")
    def test_mteane_publisher_sends_safe_event(self, mock_post):
        mock_post.return_value.status_code = 200

        result = publish_mteane_event(
            "job.new_role",
            {
                "job_title": "Backend Engineer",
                "resume_text": "private",
                "nested": {"api_key": "secret", "safe": "value"},
            },
            idempotency_key="alert-1",
        )

        self.assertTrue(result.delivered)
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["headers"]["x-api-key"], "test-key")
        self.assertEqual(kwargs["json"]["event_type"], "job.new_role")
        self.assertEqual(kwargs["json"]["idempotency_key"], "alert-1")
        self.assertEqual(kwargs["json"]["payload"]["resume_text"], "[redacted]")
        self.assertEqual(kwargs["json"]["payload"]["nested"]["api_key"], "[redacted]")
        self.assertEqual(kwargs["json"]["payload"]["nested"]["safe"], "value")

    @override_settings(MTEANE_ENABLED=True, MTEANE_API_URL="http://mteane:3000", MTEANE_API_KEY="test-key")
    @patch("notifications.mteane.requests.post")
    def test_mteane_publisher_fails_open_on_timeout(self, mock_post):
        mock_post.side_effect = requests.Timeout("slow")

        result = publish_mteane_event("scan.failed", {"company_name": "Acme"})

        self.assertFalse(result.delivered)
        self.assertEqual(result.status, "request_failed")

    def test_payload_redaction_is_recursive(self):
        payload = redact_payload({"safe": "yes", "items": [{"token": "secret"}, {"name": "ok"}]})

        self.assertEqual(payload["safe"], "yes")
        self.assertEqual(payload["items"][0]["token"], "[redacted]")
        self.assertEqual(payload["items"][1]["name"], "ok")

    @patch("companies.services.publish_mteane_event")
    def test_new_role_alert_emits_mteane_event_without_description(self, mock_publish):
        company = Company.objects.create(name="Acme", careers_url="https://jobs.lever.co/acme", scraper_type="lever")
        scan_job = ScanJob.objects.create(
            company=company,
            status="running",
            started_at=timezone.now(),
            jobs_created=1,
        )
        job = Job.objects.create(
            company=company,
            title="Backend Engineer",
            description="Should not be sent to MTEANE.",
            location="Remote",
            apply_url="https://jobs.lever.co/acme/backend",
            source_url=company.careers_url,
            source_platform="lever",
            first_seen_at=timezone.now(),
        )

        created_count = create_new_role_alerts(scan_job)

        self.assertEqual(created_count, 1)
        mock_publish.assert_called_once()
        event_type, payload = mock_publish.call_args.args[:2]
        self.assertEqual(event_type, "job.new_role")
        self.assertEqual(payload["job_id"], job.id)
        self.assertEqual(payload["job_title"], "Backend Engineer")
        self.assertNotIn("description", payload)
