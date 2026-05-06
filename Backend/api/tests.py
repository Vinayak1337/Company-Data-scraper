import json
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from companies.models import Company, CompanyJobSource, ScanJob
from jobs.models import Job
from matching.models import MatchFeedback
from notifications.models import NotificationEvent, NotificationPreference
from profiles.models import CandidateProfile, TargetTitle, UserSearchPreference
from scrapers_engine import NormalizedJob, ScrapeResult


class V3ApiTests(TestCase):
    def test_health(self):
        response = self.client.get(reverse("api_health"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertEqual(response.json()["version"], "v3")

    @override_settings(JOB_SCOUT_REQUIRE_AUTH=True, JOB_SCOUT_API_TOKEN="secret-token")
    def test_api_token_guard_protects_api_except_health(self):
        health_response = self.client.get(reverse("api_health"))
        self.assertEqual(health_response.status_code, 200)

        unauthenticated_response = self.client.get(reverse("api_companies"))
        self.assertEqual(unauthenticated_response.status_code, 401)

        authenticated_response = self.client.get(reverse("api_companies"), HTTP_AUTHORIZATION="Bearer secret-token")
        self.assertEqual(authenticated_response.status_code, 200)

    def test_company_can_be_created_without_careers_url(self):
        response = self.client.post(
            reverse("api_companies"),
            data=json.dumps({"name": "Acme", "domain": "acme.example", "priority_tier": "high"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        company = Company.objects.get(name="Acme")
        self.assertEqual(company.source_health, "needs_source")
        self.assertEqual(payload["domain"], "acme.example")
        self.assertIsNone(payload["primary_source"])

    def test_company_with_careers_url_creates_primary_source(self):
        response = self.client.post(
            reverse("api_companies"),
            data=json.dumps({"careers_url": "https://jobs.lever.co/acme", "name": "Acme"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["source_discovery_status"], "manual")
        self.assertEqual(payload["primary_source"]["platform"], "lever")
        self.assertEqual(CompanyJobSource.objects.filter(company__name="Acme", is_primary=True).count(), 1)

    def test_csv_import_creates_watchlist_and_source_candidates(self):
        response = self.client.post(
            reverse("api_companies_import_csv"),
            data=json.dumps({"csv": "company,domain,active\nAcme,acme.example,true\n"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        company = Company.objects.get(name="Acme")
        self.assertEqual(payload["created_or_updated"], 1)
        self.assertGreaterEqual(company.job_sources.count(), 1)
        self.assertIn(company.source_discovery_status, {"needs_review", "found"})

    def test_manual_source_override_sets_primary_source(self):
        company = Company.objects.create(name="Acme", domain="acme.example", source_health="needs_source")

        response = self.client.post(
            reverse("api_company_sources", args=[company.id]),
            data=json.dumps({"url": "https://boards.greenhouse.io/acme", "is_primary": True}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        company.refresh_from_db()
        self.assertEqual(company.careers_url, "https://boards.greenhouse.io/acme")
        self.assertEqual(company.scraper_type, "greenhouse")
        self.assertEqual(response.json()["status"], "active")

    def test_source_discovery_generates_reviewable_candidates(self):
        company = Company.objects.create(name="Acme", domain="acme.example", homepage_url="https://acme.example")

        response = self.client.post(reverse("api_company_discover_source", args=[company.id]))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreaterEqual(len(payload["sources"]), 1)
        self.assertIn(payload["company"]["source_discovery_status"], {"needs_review", "found"})

    @patch("companies.services.scrape")
    def test_company_crawl_persists_jobs_matches_and_notification_events(self, mock_scrape):
        profile = CandidateProfile.objects.create(
            full_name="Candidate",
            skills=["python", "django"],
            summary="Senior backend engineer",
            remote_preference="remote",
            target_locations=["Remote"],
        )
        TargetTitle.objects.create(profile=profile, title="Python Engineer", status="accepted")
        UserSearchPreference.objects.create(profile=profile, minimum_match_score=50, minimum_confidence_score=30)
        company = Company.objects.create(
            name="Acme",
            careers_url="https://jobs.lever.co/acme",
            scraper_type="lever",
            source_health="needs_setup",
            source_discovery_confidence=100,
        )
        CompanyJobSource.objects.create(
            company=company,
            url=company.careers_url,
            platform="lever",
            status="active",
            is_primary=True,
            confidence_score=100,
        )
        mock_scrape.return_value = ScrapeResult(
            "lever",
            "Acme",
            [
                NormalizedJob(
                    title="Python Engineer",
                    company_name="Acme",
                    location="Remote",
                    description="Build Django services with Python",
                    apply_url="https://jobs.lever.co/acme/1",
                    source_url=company.careers_url,
                    source_platform="lever",
                    tags=["python", "django"],
                    remote_policy="remote",
                )
            ],
        )

        response = self.client.post(reverse("api_company_crawl", args=[company.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["jobs_created"], 1)
        job = Job.objects.get(company=company)
        self.assertTrue(job.match_report.should_notify)
        self.assertEqual(ScanJob.objects.filter(company=company, status="success").count(), 1)
        self.assertEqual(NotificationEvent.objects.filter(job=job).count(), 1)

    def test_job_feedback_persists_and_updates_match(self):
        profile = CandidateProfile.objects.create(skills=["python"], summary="Backend engineer")
        TargetTitle.objects.create(profile=profile, title="Backend Engineer", status="accepted")
        company = Company.objects.create(name="Acme", careers_url="https://jobs.lever.co/acme", source_discovery_confidence=100)
        job = Job.objects.create(
            company=company,
            title="Backend Engineer",
            location="Remote",
            description="Python services",
            apply_url="https://jobs.lever.co/acme/backend",
            source_url=company.careers_url,
            source_platform="lever",
            remote_policy="remote",
        )

        response = self.client.post(
            reverse("api_job_feedback", args=[job.id]),
            data=json.dumps({"feedback_type": "bad_match", "notes": "Wrong product area"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(MatchFeedback.objects.filter(job=job, feedback_type="bad_match").count(), 1)
        self.assertEqual(response.json()["feedback"]["feedback_type"], "bad_match")

    def test_notification_preferences_include_thresholds(self):
        response = self.client.patch(
            reverse("api_notification_preferences"),
            data=json.dumps(
                {
                    "email_address": "candidate@example.com",
                    "digest_enabled": True,
                    "digest_frequency": "daily",
                    "minimum_match_score": 82,
                    "minimum_confidence_score": 60,
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        preference = NotificationPreference.objects.get()
        self.assertEqual(preference.email_address, "candidate@example.com")
        self.assertEqual(preference.minimum_match_score, 82)
        self.assertEqual(response.json()["minimum_confidence_score"], 60)

    def test_agents_support_v3_agent_types(self):
        response = self.client.post(
            reverse("api_agent_runs"),
            data=json.dumps({"agent_type": "source_discovery", "provider": "direct_api", "tool_policy": "read_only"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["agent_type"], "source_discovery")
        self.assertIn(response.json()["status"], {"success", "waiting_approval"})

    def test_cli_providers_are_local_only_and_guarded(self):
        response = self.client.get(reverse("api_agent_providers"))

        self.assertEqual(response.status_code, 200)
        gemini = next(item for item in response.json()["results"] if item["provider"] == "gemini_cli")
        self.assertTrue(gemini["is_local_only"])
        self.assertEqual(gemini["runtime_scope"], "local_cli")

        update_response = self.client.patch(
            reverse("api_agent_provider_detail", args=["gemini_cli"]),
            data=json.dumps({"enabled": True}),
            content_type="application/json",
        )

        self.assertEqual(update_response.status_code, 400)
        self.assertIn("JOB_SCOUT_ENABLE_LOCAL_CLI", update_response.json()["error"])
