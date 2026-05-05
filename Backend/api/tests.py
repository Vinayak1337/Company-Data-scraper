import json
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from agents.models import AgentArtifact, AgentAuditLog, AgentDecision, AgentProviderSetting, AgentRun, AgentStep, RuntimeInvocation
from agents.services import ensure_provider_settings
from analytics.models import AlertFeedback, LearningChange, MatchScoreCorrection, WeeklyReview
from applications.models import Application, ApplicationArtifact, TodayAction
from companies.models import Company, JobAlert, ScanJob, ScrapeLog
from intelligence.models import CompanyIntelligence, RecruiterContact
from interviews.models import InterviewPrep, OfferSupport
from jobs.models import Job
from matching.models import JobMatch
from matching.services import refresh_job_match
from notifications.models import NotificationPreference
from profiles.models import CandidateProfile, ProfileClaim, TargetTitle
from scrapers_engine import NormalizedJob, ScrapeResult


class ApiTests(TestCase):
    def test_health(self):
        response = self.client.get(reverse("api_health"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    @override_settings(JOB_SCOUT_REQUIRE_AUTH=True, JOB_SCOUT_API_TOKEN="secret-token")
    def test_api_token_guard_protects_api_except_health(self):
        health_response = self.client.get(reverse("api_health"))
        self.assertEqual(health_response.status_code, 200)

        unauthenticated_response = self.client.get(reverse("api_companies"))
        self.assertEqual(unauthenticated_response.status_code, 401)

        authenticated_response = self.client.get(reverse("api_companies"), HTTP_AUTHORIZATION="Bearer secret-token")
        self.assertEqual(authenticated_response.status_code, 200)

    @override_settings(JOB_SCOUT_REQUIRE_AUTH=True, JOB_SCOUT_API_TOKEN="")
    def test_api_token_guard_requires_configured_token(self):
        response = self.client.get(reverse("api_companies"))

        self.assertEqual(response.status_code, 503)
        self.assertIn("JOB_SCOUT_API_TOKEN", response.json()["error"])

    def test_companies_post_json(self):
        response = self.client.post(
            reverse("api_companies"),
            data='{"careers_url": "https://boards.greenhouse.io/acme", "name": "Acme"}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        company = Company.objects.get(careers_url="https://boards.greenhouse.io/acme")
        self.assertEqual(company.scraper_type, "greenhouse")
        self.assertEqual(payload["source_health"], "needs_setup")
        self.assertEqual(payload["priority_tier"], "normal")

    def test_companies_post_rejects_private_careers_url(self):
        response = self.client.post(
            reverse("api_companies"),
            data='{"careers_url": "http://127.0.0.1:9000/jobs", "name": "Local"}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("public hostname", response.json()["error"])
        self.assertFalse(Company.objects.filter(name="Local").exists())

    def test_companies_post_json_coerces_filter_fields(self):
        response = self.client.post(
            reverse("api_companies"),
            data=(
                '{"careers_url": "https://jobs.lever.co/acme", "name": "Acme", '
                '"title_keywords": "Backend, Data\\nPlatform", '
                '"negative_title_keywords": ["Manager", "Director"], '
                '"location_keywords": ["Remote", "India"], '
                '"work_mode_filter": "wfh"}'
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        company = Company.objects.get(careers_url="https://jobs.lever.co/acme")
        self.assertEqual(company.title_keywords, ["Backend", "Data", "Platform"])
        self.assertEqual(company.negative_title_keywords, ["Manager", "Director"])
        self.assertEqual(company.location_keywords, ["Remote", "India"])
        self.assertEqual(company.work_mode_filter, "remote")
        self.assertEqual(payload["title_keywords"], ["Backend", "Data", "Platform"])
        self.assertEqual(payload["work_mode_filter"], "remote")

    def test_companies_list_includes_scan_metadata(self):
        Company.objects.create(
            name="Acme",
            careers_url="https://jobs.lever.co/acme",
            scraper_type="lever",
            priority_tier="high",
            source_health="active",
        )

        response = self.client.get(reverse("api_companies"))

        self.assertEqual(response.status_code, 200)
        acme = next(company for company in response.json()["results"] if company["name"] == "Acme")
        self.assertEqual(acme["priority"], "high")
        self.assertEqual(acme["source_health"], "active")
        self.assertEqual(acme["state"], "active")

    def test_company_detail_update_delete(self):
        company = Company.objects.create(name="Acme", careers_url="https://jobs.lever.co/acme", scraper_type="lever")

        detail_url = reverse("api_company_detail", args=[company.id])
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "Acme")

        response = self.client.patch(
            detail_url,
            data='{"name": "Acme Labs", "priority_tier": "high"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "Acme Labs")
        self.assertEqual(response.json()["priority_tier"], "high")

        response = self.client.patch(
            detail_url,
            data='{"careers_url": "http://localhost:9000/jobs"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("public hostname", response.json()["error"])

        response = self.client.patch(
            detail_url,
            data=(
                '{"title_keywords": ["Python"], "location_keywords": "India, Remote", '
                '"work_mode_filter": "hybrid", "scan_frequency_hours": 12, "alert_new_roles": false}'
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["title_keywords"], ["Python"])
        self.assertEqual(response.json()["location_keywords"], ["India", "Remote"])
        self.assertEqual(response.json()["work_mode_filter"], "hybrid")
        self.assertEqual(response.json()["scan_frequency_hours"], 12)
        self.assertFalse(response.json()["alert_new_roles"])

        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Company.objects.filter(id=company.id).exists())

    def test_company_detail_rejects_invalid_filter_payload(self):
        company = Company.objects.create(name="Acme", careers_url="https://jobs.lever.co/acme", scraper_type="lever")

        response = self.client.patch(
            reverse("api_company_detail", args=[company.id]),
            data='{"work_mode_filter": "spaceship"}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("work_mode_filter", response.json()["error"])

    def test_company_pause_resume(self):
        company = Company.objects.create(name="Acme", careers_url="https://jobs.lever.co/acme", scraper_type="lever")

        response = self.client.post(reverse("api_company_pause", args=[company.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["state"], "paused")
        company.refresh_from_db()
        self.assertFalse(company.is_active)
        self.assertEqual(company.source_health, "paused")

        response = self.client.post(reverse("api_company_resume", args=[company.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["state"], "active")
        company.refresh_from_db()
        self.assertTrue(company.is_active)
        self.assertEqual(company.source_health, "needs_setup")

    def test_company_intelligence_and_recruiter_contacts(self):
        company = Company.objects.create(name="Acme", careers_url="https://jobs.lever.co/acme", scraper_type="lever")
        Job.objects.create(
            company=company,
            title="Backend Platform Engineer",
            location="Remote",
            apply_url="https://jobs.lever.co/acme/backend-platform",
            source_url=company.careers_url,
            source_platform="lever",
            remote_policy="remote",
        )

        intelligence_response = self.client.post(reverse("api_company_intelligence", args=[company.id]))
        contact_response = self.client.post(
            reverse("api_company_recruiter_contacts", args=[company.id]),
            data=json.dumps({"name": "A Recruiter", "title": "Technical Recruiter", "status": "lead"}),
            content_type="application/json",
        )
        company_response = self.client.get(reverse("api_company_detail", args=[company.id]))

        self.assertEqual(intelligence_response.status_code, 201)
        self.assertTrue(intelligence_response.json()["hiring_signals"])
        self.assertEqual(intelligence_response.json()["role_legitimacy"], "likely_legitimate")
        self.assertTrue(intelligence_response.json()["caveats"])
        self.assertEqual(intelligence_response.json()["verification_status"], "deterministic")
        self.assertEqual(contact_response.status_code, 201)
        self.assertEqual(CompanyIntelligence.objects.filter(company=company).count(), 1)
        self.assertEqual(RecruiterContact.objects.filter(company=company).count(), 1)
        self.assertIsNotNone(company_response.json()["latest_intelligence"])
        self.assertEqual(company_response.json()["recruiter_contacts_count"], 1)

    @patch("companies.services.scrape")
    def test_company_rescan_success(self, mock_scrape):
        company = Company.objects.create(name="Acme", careers_url="https://jobs.lever.co/acme", scraper_type="lever")
        mock_scrape.return_value = ScrapeResult(
            "lever",
            "Acme",
            [
                NormalizedJob(
                    title="Python Engineer",
                    company_name="Acme",
                    location="Remote",
                    description="Build Django services",
                    apply_url="https://jobs.lever.co/acme/1",
                    source_url=company.careers_url,
                    source_platform="lever",
                    tags=["python"],
                    remote_policy="remote",
                )
            ],
        )

        response = self.client.post(reverse("api_company_rescan", args=[company.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(response.json()["jobs_created"], 1)
        self.assertEqual(response.json()["alerts_created"], 1)
        company.refresh_from_db()
        self.assertEqual(company.source_health, "active")
        self.assertEqual(company.consecutive_failure_count, 0)
        self.assertIsNotNone(company.last_successful_scan_at)
        self.assertIsNotNone(company.last_new_role_at)
        self.assertEqual(ScanJob.objects.filter(company=company, status="success").count(), 1)
        self.assertEqual(JobAlert.objects.filter(company=company, status="unread").count(), 1)

    @patch("companies.services.scrape")
    def test_company_rescan_applies_company_filters(self, mock_scrape):
        company = Company.objects.create(
            name="Acme",
            careers_url="https://jobs.lever.co/acme",
            scraper_type="lever",
            title_keywords=["Engineer"],
            negative_title_keywords=["Manager"],
            location_keywords=["Remote"],
            work_mode_filter="remote",
        )
        mock_scrape.return_value = ScrapeResult(
            "lever",
            "Acme",
            [
                NormalizedJob(
                    title="Backend Engineer",
                    company_name="Acme",
                    location="Remote",
                    description="Build services",
                    apply_url="https://jobs.lever.co/acme/1",
                    source_url=company.careers_url,
                    source_platform="lever",
                    remote_policy="remote",
                ),
                NormalizedJob(
                    title="Engineering Manager",
                    company_name="Acme",
                    location="Remote",
                    description="Manage services",
                    apply_url="https://jobs.lever.co/acme/2",
                    source_url=company.careers_url,
                    source_platform="lever",
                    remote_policy="remote",
                ),
                NormalizedJob(
                    title="Backend Engineer",
                    company_name="Acme",
                    location="New York",
                    description="Build services",
                    apply_url="https://jobs.lever.co/acme/3",
                    source_url=company.careers_url,
                    source_platform="lever",
                    remote_policy="remote",
                ),
                NormalizedJob(
                    title="Backend Engineer",
                    company_name="Acme",
                    location="Remote",
                    description="Build services",
                    apply_url="https://jobs.lever.co/acme/4",
                    source_url=company.careers_url,
                    source_platform="lever",
                    remote_policy="onsite",
                ),
            ],
        )

        response = self.client.post(reverse("api_company_rescan", args=[company.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["jobs_found"], 4)
        self.assertEqual(response.json()["jobs_created"], 1)
        self.assertEqual(list(Job.objects.values_list("apply_url", flat=True)), ["https://jobs.lever.co/acme/1"])

    @patch("companies.services.scrape")
    def test_company_rescan_failure(self, mock_scrape):
        company = Company.objects.create(name="Acme", careers_url="https://jobs.lever.co/acme", scraper_type="lever")
        mock_scrape.side_effect = RuntimeError("source unavailable")

        response = self.client.post(reverse("api_company_rescan", args=[company.id]))

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["status"], "failed")
        company.refresh_from_db()
        self.assertEqual(company.source_health, "degraded")
        self.assertEqual(company.consecutive_failure_count, 1)
        self.assertIsNotNone(company.last_failed_scan_at)

    @patch("companies.services.scrape")
    def test_company_rescan_paused_company_does_not_invoke_scraper(self, mock_scrape):
        company = Company.objects.create(
            name="Acme",
            careers_url="https://jobs.lever.co/acme",
            scraper_type="lever",
            is_active=False,
            source_health="paused",
        )

        response = self.client.post(reverse("api_company_rescan", args=[company.id]))

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["status"], "failed")
        self.assertIn("paused", response.json()["message"])
        self.assertEqual(response.json()["scan_job"]["status"], "skipped")
        mock_scrape.assert_not_called()

    @patch("companies.services.scrape")
    def test_company_rescan_prevents_overlapping_scan(self, mock_scrape):
        company = Company.objects.create(name="Acme", careers_url="https://jobs.lever.co/acme", scraper_type="lever")
        ScanJob.objects.create(company=company, status="running", trigger="manual")

        response = self.client.post(reverse("api_company_rescan", args=[company.id]))

        self.assertEqual(response.status_code, 409)
        self.assertIn("already has", response.json()["error"])
        mock_scrape.assert_not_called()

    @patch("companies.services.scrape")
    def test_company_scrape_legacy_route_still_scans(self, mock_scrape):
        company = Company.objects.create(name="Acme", careers_url="https://jobs.lever.co/acme", scraper_type="lever")
        mock_scrape.return_value = ScrapeResult("lever", "Acme", [])

        response = self.client.post(reverse("api_company_scrape", args=[company.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        self.assertIn("jobs_found", response.json())

    def test_company_logs_returns_recent_logs(self):
        company = Company.objects.create(name="Acme", careers_url="https://jobs.lever.co/acme", scraper_type="lever")
        ScrapeLog.objects.create(company=company, status="success", jobs_found=1, jobs_created=1)
        ScrapeLog.objects.create(company=company, status="failed", message="source unavailable")

        response = self.client.get(reverse("api_company_logs", args=[company.id]), {"limit": "1"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["results"][0]["company_id"], company.id)
        self.assertIn(payload["results"][0]["status"], {"success", "failed"})

    def test_company_logs_all_returns_recent_logs_with_company_name(self):
        company = Company.objects.create(name="Acme", careers_url="https://jobs.lever.co/acme", scraper_type="lever")
        ScrapeLog.objects.create(company=company, status="success", jobs_found=1, jobs_created=1)

        response = self.client.get(reverse("api_company_logs_all"), {"limit": "5"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["results"][0]["company_name"], "Acme")

    @override_settings(SCANNER_ENABLED=True)
    @patch.dict("os.environ", {"OPENAI_API_KEY": "super-secret-ai-key", "EMAIL_HOST": "smtp.example", "EMAIL_HOST_PASSWORD": "super-secret-smtp-password"})
    def test_diagnostics_returns_status_counts_without_secrets(self):
        starting_companies = Company.objects.count()
        company = Company.objects.create(name="Acme", careers_url="https://jobs.lever.co/acme", scraper_type="lever")
        Job.objects.create(company=company, title="Frontend Engineer", location="Remote", apply_url="https://x/1", source_url=company.careers_url, source_platform="lever")
        ScrapeLog.objects.create(company=company, status="success", jobs_found=1)

        response = self.client.get(reverse("api_diagnostics"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["database"]["status"], "ok")
        self.assertIn(payload["scheduler"]["status"], {"ok", "error"})
        self.assertTrue(payload["scheduler"]["configured"])
        self.assertIn("queued_runs", payload["worker"])
        self.assertIn("langsmith", payload)
        self.assertTrue(payload["ai"]["configured"])
        self.assertTrue(payload["smtp"]["configured"])
        self.assertEqual(payload["core_counts"]["companies"], starting_companies + 1)
        self.assertEqual(payload["core_counts"]["jobs"], 1)
        self.assertIn("scan_jobs", payload["core_counts"])
        self.assertIn("unread_alerts", payload["core_counts"])
        body = response.content.decode()
        self.assertNotIn("super-secret-ai-key", body)
        self.assertNotIn("super-secret-smtp-password", body)

    @override_settings(SECRET_KEY="super-secret-django-key", APP_VERSION="test-version")
    @patch.dict("os.environ", {"OPENAI_API_KEY": "super-secret-ai-key"})
    def test_export_returns_data_without_config_secrets(self):
        company = Company.objects.create(name="Acme", careers_url="https://jobs.lever.co/acme", scraper_type="lever")
        Job.objects.create(company=company, title="Frontend Engineer", location="Remote", apply_url="https://x/1", source_url=company.careers_url, source_platform="lever")
        ScrapeLog.objects.create(company=company, status="failed", message="export-secret-log-message")

        response = self.client.get(reverse("api_export"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["app_version"], "test-version")
        self.assertIn("schema_version", payload)
        self.assertTrue(any(item["careers_url"] == company.careers_url for item in payload["companies"]))
        self.assertEqual(len(payload["jobs"]), 1)
        self.assertEqual(len(payload["scan_logs"]), 1)
        self.assertIn("scan_jobs", payload)
        self.assertIn("alerts", payload)
        body = response.content.decode()
        self.assertNotIn("super-secret-django-key", body)
        self.assertNotIn("super-secret-ai-key", body)
        self.assertNotIn("export-secret-log-message", body)
        self.assertEqual(JobMatch.objects.count(), 0)

    def test_import_companies_creates_updates_and_reports_errors(self):
        existing = Company.objects.create(
            name="Acme",
            careers_url="https://jobs.lever.co/acme",
            scraper_type="lever",
            title_keywords=["Old"],
        )

        response = self.client.post(
            reverse("api_import_companies"),
            data=(
                '{"companies": ['
                '{"careers_url": "https://jobs.lever.co/acme", "name": "Acme Labs", "title_keywords": ["Backend"], "work_mode_filter": "remote"},'
                '{"careers_url": "https://boards.greenhouse.io/zen", "name": "Zen", "location_keywords": "India, Remote"},'
                '{"name": "Missing URL"},'
                '{"careers_url": "https://jobs.lever.co/bad", "work_mode_filter": "invalid"}'
                "]}"
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["created_count"], 1)
        self.assertEqual(payload["updated_count"], 1)
        self.assertEqual(payload["error_count"], 2)
        existing.refresh_from_db()
        self.assertEqual(existing.name, "Acme Labs")
        self.assertEqual(existing.title_keywords, ["Backend"])
        self.assertEqual(existing.work_mode_filter, "remote")
        self.assertTrue(Company.objects.filter(careers_url="https://boards.greenhouse.io/zen").exists())
        self.assertIn("careers_url is required", payload["errors"][0]["error"])

    def test_import_companies_accepts_raw_list(self):
        response = self.client.post(
            reverse("api_import_companies"),
            data='[{"careers_url": "https://jobs.lever.co/raw", "name": "Raw Co"}]',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["created_count"], 1)
        self.assertTrue(Company.objects.filter(careers_url="https://jobs.lever.co/raw").exists())

    def test_import_companies_accepts_watchlist_alias_route(self):
        response = self.client.post(
            reverse("api_companies_import"),
            data='{"watchlist": [{"careers_url": "https://jobs.lever.co/watch", "name": "Watch Co"}]}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["created_count"], 1)
        self.assertTrue(Company.objects.filter(careers_url="https://jobs.lever.co/watch").exists())

    def test_workspace_export_can_be_deleted_and_restored(self):
        profile = CandidateProfile.objects.create(full_name="Jane Dev", skills=["Python"], cv_markdown="# CV")
        TargetTitle.objects.create(profile=profile, title="Backend Engineer", status="accepted")
        company = Company.objects.create(name="Acme", careers_url="https://jobs.lever.co/acme", scraper_type="lever")
        job = Job.objects.create(
            company=company,
            title="Backend Engineer",
            location="Remote",
            apply_url="https://jobs.lever.co/acme/backend",
            source_url=company.careers_url,
            source_platform="lever",
        )
        application = Application.objects.create(job=job, status="saved", notes="Keep these notes", next_action="Tailor CV")
        ApplicationArtifact.objects.create(
            application=application,
            artifact_type="tailoring_plan",
            title="Plan",
            content="Use Python evidence.",
        )
        agent_run = AgentRun.objects.create(
            agent_type="profile_builder",
            status="success",
            provider="direct_api",
            tool_policy="read_only",
            input_snapshot={"profile": {"cv_markdown": "# private cv", "skills": ["Python"]}},
            output_snapshot={"readiness_score": 75},
            result_summary="Profile review complete.",
        )
        AgentStep.objects.create(run=agent_run, order=1, name="Review", status="success")
        AgentArtifact.objects.create(run=agent_run, artifact_type="markdown", title="Review", content="Useful artifact")
        AgentDecision.objects.create(run=agent_run, decision_type="profile_review", question="Review?", status="approved")
        RuntimeInvocation.objects.create(
            run=agent_run,
            provider="direct_api",
            adapter="local_profile_builder",
            status="success",
            output_snapshot={"ok": True},
        )
        AgentAuditLog.objects.create(run=agent_run, event_type="run_finished", message="Done")
        CompanyIntelligence.objects.create(company=company, summary="Public-source note.")
        WeeklyReview.objects.create(period_start=timezone.now(), period_end=timezone.now(), summary="Review")

        export_response = self.client.get(reverse("api_export"))
        delete_response = self.client.post(
            reverse("api_delete_personal_data"),
            data=json.dumps({"confirmation": "DELETE ALL PERSONAL DATA"}),
            content_type="application/json",
        )
        self.assertEqual(export_response.status_code, 200)
        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(Company.objects.count(), 0)

        restore_response = self.client.post(
            reverse("api_import_workspace"),
            data=json.dumps(export_response.json()),
            content_type="application/json",
        )

        self.assertIn(restore_response.status_code, {200, 207})
        self.assertTrue(Company.objects.filter(careers_url="https://jobs.lever.co/acme").exists())
        self.assertTrue(Job.objects.filter(apply_url="https://jobs.lever.co/acme/backend").exists())
        restored_application = Application.objects.get(job__apply_url="https://jobs.lever.co/acme/backend")
        self.assertEqual(restored_application.notes, "Keep these notes")
        self.assertTrue(CandidateProfile.objects.filter(full_name="Jane Dev").exists())
        restored_run = AgentRun.objects.get(result_summary="Profile review complete.")
        self.assertEqual(restored_run.steps.count(), 1)
        self.assertEqual(restored_run.artifacts.count(), 1)
        self.assertEqual(restored_run.decisions.count(), 1)
        self.assertEqual(restored_run.runtime_invocations.count(), 1)
        self.assertEqual(restored_run.audit_logs.count(), 1)
        self.assertNotIn("# private cv", json.dumps(export_response.json()))

    def test_delete_all_personal_data_requires_confirmation(self):
        Company.objects.create(name="Acme", careers_url="https://jobs.lever.co/acme", scraper_type="lever")

        response = self.client.post(
            reverse("api_delete_personal_data"),
            data=json.dumps({"confirmation": "delete"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertTrue(Company.objects.filter(name="Acme").exists())

    def test_redaction_audit_is_available_without_secrets(self):
        response = self.client.get(reverse("api_redaction_audit"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertTrue(payload["checks"])

    def test_jobs_list(self):
        company = Company.objects.create(name="Acme", careers_url="https://jobs.lever.co/acme", scraper_type="lever")
        Job.objects.create(company=company, title="Frontend Engineer", location="Bengaluru, India", apply_url="https://x/1", source_url=company.careers_url, source_platform="lever", tags=["react"])

        response = self.client.get(reverse("api_jobs"), {"tech": "react"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

    @patch("companies.services.scrape")
    def test_scan_run_scans_due_companies_and_creates_deduped_alerts(self, mock_scrape):
        company = Company.objects.create(name="Acme", careers_url="https://jobs.lever.co/acme", scraper_type="lever")
        mock_scrape.return_value = ScrapeResult(
            "lever",
            "Acme",
            [
                NormalizedJob(
                    title="Platform Engineer",
                    company_name="Acme",
                    location="Remote",
                    description="Build platform services",
                    apply_url="https://jobs.lever.co/acme/platform",
                    source_url=company.careers_url,
                    source_platform="lever",
                    remote_policy="remote",
                )
            ],
        )

        first_response = self.client.post(
            reverse("api_scan_run"),
            data=f'{{"company_id": {company.id}}}',
            content_type="application/json",
        )
        second_response = self.client.post(
            reverse("api_scan_run"),
            data=f'{{"company_id": {company.id}}}',
            content_type="application/json",
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(first_response.json()["scanned"], 1)
        self.assertEqual(first_response.json()["alerts_created"], 1)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(second_response.json()["alerts_created"], 0)
        self.assertEqual(Job.objects.count(), 1)
        self.assertEqual(JobAlert.objects.count(), 1)

    def test_scan_run_dry_run_reports_due_companies_without_scanning(self):
        Company.objects.create(name="Acme", careers_url="https://jobs.lever.co/acme", scraper_type="lever")

        response = self.client.post(reverse("api_scan_run"), data='{"dry_run": true}', content_type="application/json")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreaterEqual(payload["due_count"], 1)
        self.assertEqual(payload["scanned"], 0)
        self.assertEqual(ScanJob.objects.count(), 0)

    def test_scan_jobs_and_alerts_endpoints(self):
        company = Company.objects.create(name="Acme", careers_url="https://jobs.lever.co/acme", scraper_type="lever")
        job = Job.objects.create(
            company=company,
            title="Frontend Engineer",
            location="Remote",
            apply_url="https://jobs.lever.co/acme/frontend",
            source_url=company.careers_url,
            source_platform="lever",
        )
        scan_job = ScanJob.objects.create(company=company, status="success", jobs_created=1)
        alert = JobAlert.objects.create(
            company=company,
            job=job,
            scan_job=scan_job,
            title="New role at Acme: Frontend Engineer",
        )

        scans_response = self.client.get(reverse("api_scan_jobs"))
        alerts_response = self.client.get(reverse("api_alerts"), {"status": "unread"})
        read_response = self.client.post(reverse("api_alert_read", args=[alert.id]))
        dismiss_response = self.client.post(reverse("api_alert_dismiss", args=[alert.id]))

        self.assertEqual(scans_response.status_code, 200)
        self.assertEqual(scans_response.json()["results"][0]["id"], scan_job.id)
        self.assertEqual(alerts_response.status_code, 200)
        self.assertEqual(alerts_response.json()["count"], 1)
        self.assertEqual(read_response.status_code, 200)
        self.assertEqual(read_response.json()["status"], "read")
        self.assertEqual(dismiss_response.status_code, 200)
        self.assertEqual(dismiss_response.json()["status"], "dismissed")

    @patch("companies.services.scrape")
    def test_scan_due_companies_command_runs_without_ui(self, mock_scrape):
        Company.objects.create(name="Acme", careers_url="https://jobs.lever.co/acme", scraper_type="lever")
        mock_scrape.return_value = ScrapeResult("lever", "Acme", [])

        starting_count = ScanJob.objects.filter(status="success").count()
        call_command("scan_due_companies", "--limit", "5")

        self.assertEqual(ScanJob.objects.filter(status="success").count(), starting_count + 5)

    def test_today_actions_are_created_from_unread_role_alerts(self):
        company = Company.objects.create(name="Acme", careers_url="https://jobs.lever.co/acme", scraper_type="lever")
        job = Job.objects.create(
            company=company,
            title="Backend Engineer",
            location="Remote",
            apply_url="https://jobs.lever.co/acme/backend",
            source_url=company.careers_url,
            source_platform="lever",
        )
        alert = JobAlert.objects.create(company=company, job=job, title="New role at Acme: Backend Engineer")

        response = self.client.get(reverse("api_today_actions"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["results"][0]["source_alert_id"], alert.id)
        self.assertEqual(payload["results"][0]["action_type"], "review_new_role")

    def test_alert_save_and_skip_create_application_records(self):
        company = Company.objects.create(name="Acme", careers_url="https://jobs.lever.co/acme", scraper_type="lever")
        save_job = Job.objects.create(
            company=company,
            title="Backend Engineer",
            location="Remote",
            apply_url="https://jobs.lever.co/acme/backend",
            source_url=company.careers_url,
            source_platform="lever",
        )
        skip_job = Job.objects.create(
            company=company,
            title="Frontend Engineer",
            location="Remote",
            apply_url="https://jobs.lever.co/acme/frontend",
            source_url=company.careers_url,
            source_platform="lever",
        )
        save_alert = JobAlert.objects.create(company=company, job=save_job, title="New role at Acme: Backend Engineer")
        skip_alert = JobAlert.objects.create(company=company, job=skip_job, title="New role at Acme: Frontend Engineer")
        self.client.get(reverse("api_today_actions"))

        save_response = self.client.post(
            reverse("api_alert_save_application", args=[save_alert.id]),
            data='{"next_action": "Tailor CV", "status": "saved"}',
            content_type="application/json",
        )
        skip_response = self.client.post(
            reverse("api_alert_skip_application", args=[skip_alert.id]),
            data='{"notes": "Not enough backend scope"}',
            content_type="application/json",
        )

        self.assertEqual(save_response.status_code, 201)
        self.assertEqual(save_response.json()["status"], "saved")
        self.assertEqual(skip_response.status_code, 201)
        self.assertEqual(skip_response.json()["status"], "skipped")
        save_alert.refresh_from_db()
        skip_alert.refresh_from_db()
        self.assertEqual(save_alert.status, "read")
        self.assertEqual(skip_alert.status, "dismissed")
        self.assertEqual(Application.objects.count(), 2)
        self.assertFalse(TodayAction.objects.filter(status="open", source_alert__in=[save_alert, skip_alert]).exists())

    def test_application_update_followup_creates_today_action(self):
        company = Company.objects.create(name="Acme", careers_url="https://jobs.lever.co/acme", scraper_type="lever")
        job = Job.objects.create(
            company=company,
            title="Platform Engineer",
            location="Remote",
            apply_url="https://jobs.lever.co/acme/platform",
            source_url=company.careers_url,
            source_platform="lever",
        )
        application = Application.objects.create(job=job, status="applied")
        due_at = timezone.now().isoformat()

        response = self.client.patch(
            reverse("api_application_detail", args=[application.id]),
            data=f'{{"next_action": "Follow up with recruiter", "follow_up_at": "{due_at}"}}',
            content_type="application/json",
        )
        today_response = self.client.get(reverse("api_today_actions"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["next_action"], "Follow up with recruiter")
        self.assertEqual(today_response.status_code, 200)
        actions = today_response.json()["results"]
        self.assertTrue(any(action["application_id"] == application.id and action["action_type"] == "follow_up" for action in actions))

    def test_applications_endpoint_create_list_and_status_update(self):
        company = Company.objects.create(name="Acme", careers_url="https://jobs.lever.co/acme", scraper_type="lever")
        job = Job.objects.create(
            company=company,
            title="Data Engineer",
            location="Remote",
            apply_url="https://jobs.lever.co/acme/data",
            source_url=company.careers_url,
            source_platform="lever",
        )

        create_response = self.client.post(
            reverse("api_applications"),
            data=f'{{"job_id": {job.id}, "status": "saved", "notes": "Looks relevant"}}',
            content_type="application/json",
        )
        application_id = create_response.json()["id"]
        update_response = self.client.patch(
            reverse("api_application_detail", args=[application_id]),
            data='{"status": "applied"}',
            content_type="application/json",
        )
        list_response = self.client.get(reverse("api_applications"), {"status": "applied"})

        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["status"], "applied")
        self.assertIsNotNone(update_response.json()["applied_at"])
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["count"], 1)

    def test_application_tailoring_artifacts_can_be_generated_and_reviewed(self):
        CandidateProfile.objects.create(
            full_name="Jane Dev",
            skills=["Python", "Django", "Postgres"],
            proof_points=[{"text": "Built Django APIs with measurable reliability improvements."}],
        )
        company = Company.objects.create(name="Acme", careers_url="https://jobs.lever.co/acme", scraper_type="lever")
        job = Job.objects.create(
            company=company,
            title="Backend Engineer",
            location="Remote",
            description="Python Django Postgres APIs",
            apply_url="https://jobs.lever.co/acme/backend",
            source_url=company.careers_url,
            source_platform="lever",
            tags=["python", "django"],
            remote_policy="remote",
        )
        application = Application.objects.create(job=job, status="saved")

        response = self.client.post(reverse("api_application_generate_tailoring", args=[application.id]))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreaterEqual(payload["count"], 5)
        self.assertTrue(ApplicationArtifact.objects.filter(application=application, artifact_type="tailoring_plan").exists())
        detail_response = self.client.get(reverse("api_application_detail", args=[application.id]))
        artifact = detail_response.json()["artifacts"][0]
        status_response = self.client.post(reverse("api_application_artifact_status", args=[artifact["id"], "approved"]))
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(status_response.json()["status"], "approved")

    def test_application_interview_prep_and_offer_support(self):
        CandidateProfile.objects.create(
            full_name="Jane Dev",
            skills=["Python", "Django"],
            proof_points=[{"text": "Built Django APIs."}],
            compensation_expectation="$100k+",
        )
        company = Company.objects.create(name="Acme", careers_url="https://jobs.lever.co/acme", scraper_type="lever")
        job = Job.objects.create(
            company=company,
            title="Backend Engineer",
            location="Remote",
            description="Python Django APIs",
            apply_url="https://jobs.lever.co/acme/backend",
            source_url=company.careers_url,
            source_platform="lever",
            tags=["python", "django"],
        )
        application = Application.objects.create(job=job, status="interviewing")

        prep_response = self.client.post(reverse("api_application_generate_interview_prep", args=[application.id]))
        offer_response = self.client.post(reverse("api_application_generate_offer_support", args=[application.id]))
        detail_response = self.client.get(reverse("api_application_detail", args=[application.id]))

        self.assertEqual(prep_response.status_code, 201)
        self.assertTrue(prep_response.json()["question_bank"])
        self.assertEqual(prep_response.json()["stage"], "technical")
        self.assertTrue(prep_response.json()["checklist"])
        self.assertEqual(offer_response.status_code, 201)
        self.assertTrue(offer_response.json()["decision_criteria"])
        self.assertTrue(offer_response.json()["manual_research"])
        self.assertEqual(InterviewPrep.objects.filter(application=application).count(), 1)
        self.assertEqual(OfferSupport.objects.filter(application=application).count(), 1)
        self.assertIsNotNone(detail_response.json()["interview_prep"])
        self.assertIsNotNone(detail_response.json()["offer_support"])

    def test_profile_get_and_update_manual_fields(self):
        response = self.client.get(reverse("api_profile"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["remote_preference"], "any")

        response = self.client.patch(
            reverse("api_profile"),
            data=(
                '{"full_name": "Jane Dev", "headline": "Backend Engineer", '
                '"location": "Bengaluru", "remote_preference": "remote", '
                '"skills": "Python, Django\\nPostgres", "target_locations": ["India", "Remote"]}'
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["full_name"], "Jane Dev")
        self.assertEqual(payload["skills"], ["Python", "Django", "Postgres"])
        self.assertEqual(payload["target_locations"], ["India", "Remote"])

    def test_profile_resume_import_generates_cv_titles_and_unconfirmed_claims(self):
        resume_text = """
Jane Dev
Experience
- Built Django APIs with Postgres and Redis for internal developer tooling.
- Improved deployment reliability by 40% using Docker, Kubernetes, and AWS.
Skills
Python, Django, Postgres, Redis, Docker, Kubernetes, AWS
"""

        response = self.client.post(
            reverse("api_profile_import_resume"),
            data=json.dumps({"resume_text": resume_text}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("# CV", payload["cv_markdown"])
        self.assertTrue(payload["target_titles"])
        backend_title = next(title for title in payload["target_titles"] if title["title"] == "Backend Engineer")
        self.assertIn(backend_title["fit_bucket"], {"core", "adjacent", "stretch"})
        self.assertGreaterEqual(backend_title["confidence_score"], 50)
        self.assertGreaterEqual(backend_title["knowledge_accuracy"], 1)
        self.assertTrue(payload["claims"])
        self.assertTrue(all(claim["status"] == "unconfirmed" for claim in payload["claims"]))
        self.assertIn("profile:", payload["profile_yml"])
        self.assertTrue(payload["proof_points"])
        self.assertTrue(payload["skill_inventory"])
        self.assertGreater(payload["profile_completeness_score"], 0)

    def test_profile_target_titles_and_claims_can_be_accepted_or_rejected(self):
        profile = CandidateProfile.objects.create(full_name="Jane Dev")
        target_title = TargetTitle.objects.create(profile=profile, title="Backend Engineer")
        claim = ProfileClaim.objects.create(profile=profile, claim_type="skill", text="Has experience with Python.")

        accept_response = self.client.post(reverse("api_target_title_status", args=[target_title.id, "accepted"]))
        reject_claim_response = self.client.post(reverse("api_profile_claim_status", args=[claim.id, "rejected"]))

        self.assertEqual(accept_response.status_code, 200)
        self.assertEqual(accept_response.json()["status"], "accepted")
        self.assertEqual(reject_claim_response.status_code, 200)
        self.assertEqual(reject_claim_response.json()["status"], "rejected")

    def test_accepted_titles_can_update_company_filters(self):
        profile = CandidateProfile.objects.create(full_name="Jane Dev")
        TargetTitle.objects.create(profile=profile, title="Backend Engineer", status="accepted")
        TargetTitle.objects.create(profile=profile, title="React Developer", status="rejected")
        company = Company.objects.create(
            name="Acme",
            careers_url="https://jobs.lever.co/acme",
            scraper_type="lever",
            title_keywords=["Python"],
        )

        response = self.client.post(reverse("api_profile_apply_titles"))

        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.json()["updated_count"], 1)
        company.refresh_from_db()
        self.assertEqual(company.title_keywords, ["Python", "Backend Engineer"])

    def test_profile_search_strategy_can_be_generated_and_applied(self):
        profile = CandidateProfile.objects.create(
            full_name="Jane Dev",
            headline="Backend Engineer",
            location="Remote",
            skills=["Python", "Django", "Postgres"],
            target_locations=["India"],
            preferred_work_modes=["remote"],
        )
        TargetTitle.objects.create(profile=profile, title="Backend Engineer", status="accepted")
        company = Company.objects.create(name="Acme", careers_url="https://jobs.lever.co/acme", scraper_type="lever")

        generate_response = self.client.post(reverse("api_profile_generate_search_strategy"))

        self.assertEqual(generate_response.status_code, 200)
        strategy = generate_response.json()
        self.assertIn("Backend Engineer", strategy["target_title_keywords"])
        self.assertIn("backend", strategy["role_families"])

        apply_response = self.client.post(reverse("api_profile_apply_search_strategy"))

        self.assertEqual(apply_response.status_code, 200)
        self.assertGreaterEqual(apply_response.json()["updated_count"], 1)
        company.refresh_from_db()
        self.assertIn("Backend Engineer", company.title_keywords)
        self.assertIn("intern", company.negative_title_keywords)
        self.assertEqual(company.work_mode_filter, "remote")

    def test_discovery_inbox_can_capture_import_and_dismiss_urls(self):
        create_response = self.client.post(
            reverse("api_discovery_inbox"),
            data=json.dumps(
                {
                    "url": "https://jobs.example.com/careers",
                    "item_type": "company",
                    "title": "Example Jobs",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(create_response.status_code, 201)
        item_id = create_response.json()["id"]
        list_response = self.client.get(reverse("api_discovery_inbox"))
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["count"], 1)

        import_response = self.client.post(reverse("api_discovery_inbox_import", args=[item_id]))

        self.assertEqual(import_response.status_code, 200)
        self.assertEqual(import_response.json()["status"], "imported")
        self.assertTrue(Company.objects.filter(careers_url="https://jobs.example.com/careers").exists())

        job_response = self.client.post(
            reverse("api_discovery_inbox"),
            data=json.dumps({"url": "https://careers.example.org/jobs/123", "item_type": "job", "title": "Platform Engineer"}),
            content_type="application/json",
        )
        self.assertEqual(job_response.status_code, 201)
        dismiss_response = self.client.post(reverse("api_discovery_inbox_dismiss", args=[job_response.json()["id"]]))
        self.assertEqual(dismiss_response.status_code, 200)
        self.assertEqual(dismiss_response.json()["status"], "dismissed")

    def test_discovery_inbox_rejects_private_urls(self):
        response = self.client.post(
            reverse("api_discovery_inbox"),
            data=json.dumps({"url": "http://localhost:9000/jobs", "item_type": "job"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("public hostname", response.json()["error"])

    def test_profile_export_includes_profile_without_secrets(self):
        profile = CandidateProfile.objects.create(full_name="Jane Dev", cv_markdown="# CV\nSecret-free")
        TargetTitle.objects.create(profile=profile, title="Backend Engineer", status="accepted")

        response = self.client.get(reverse("api_export"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["profile"]["full_name"], "Jane Dev")
        self.assertEqual(payload["profile"]["target_titles"][0]["title"], "Backend Engineer")

    @patch.dict("os.environ", {"OPENAI_API_KEY": "super-secret-ai-key"})
    def test_agent_provider_defaults_do_not_expose_secrets(self):
        response = self.client.get(reverse("api_agent_providers"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 6)
        direct_api = next(provider for provider in payload["results"] if provider["provider"] == "direct_api")
        self.assertTrue(direct_api["api_key_configured"])
        self.assertEqual(direct_api["api_key_env_var"], "OPENAI_API_KEY")
        self.assertNotIn("super-secret-ai-key", response.content.decode())

    def test_agent_provider_update_controls_runtime_metadata(self):
        ensure_provider_settings()

        response = self.client.patch(
            reverse("api_agent_provider_detail", args=["direct_api"]),
            data=(
                '{"model_name": "local-reviewer", "default_tool_policy": "workspace_write", '
                '"enabled": false, "consent_required": true, "daily_run_limit": 3, '
                '"monthly_budget_cents": 500, "estimated_cost_per_run_cents": 25}'
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["model_name"], "local-reviewer")
        self.assertEqual(payload["default_tool_policy"], "workspace_write")
        self.assertFalse(payload["enabled"])
        self.assertTrue(payload["consent_required"])
        self.assertEqual(payload["daily_run_limit"], 3)
        self.assertEqual(payload["monthly_budget_cents"], 500)

    def test_agent_runtime_status_and_consent_guard(self):
        ensure_provider_settings()
        openrouter = AgentProviderSetting.objects.get(provider="openrouter")
        openrouter.enabled = True
        openrouter.consent_required = True
        openrouter.save(update_fields=["enabled", "consent_required", "updated_at"])

        blocked_response = self.client.post(
            reverse("api_agent_runs"),
            data='{"agent_type": "profile_builder", "provider": "openrouter"}',
            content_type="application/json",
        )
        status_response = self.client.get(reverse("api_agent_runtime"))

        self.assertEqual(blocked_response.status_code, 400)
        self.assertIn("consent", blocked_response.json()["error"].lower())
        self.assertEqual(status_response.status_code, 200)
        self.assertIn("providers", status_response.json())

    @override_settings(AGENT_EXECUTION_MODE="queued")
    def test_agent_queue_mode_defers_until_worker_command_runs(self):
        response = self.client.post(
            reverse("api_agent_runs"),
            data='{"agent_type": "profile_builder", "provider": "direct_api"}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "queued")

        call_command("process_agent_queue", "--limit", "1")

        run = AgentRun.objects.get(id=response.json()["id"])
        self.assertIn(run.status, {"success", "failed", "waiting_approval"})

    def test_profile_builder_agent_run_creates_reviewable_artifact_without_mutating_profile(self):
        profile = CandidateProfile.objects.create(
            full_name="Jane Dev",
            skills=["Python", "Django", "Postgres"],
            summary="Builds backend tools.",
            cv_markdown="# CV\nPython backend engineer.",
            profile_markdown="# Profile\nBackend systems.",
        )
        TargetTitle.objects.create(profile=profile, title="Backend Engineer", status="accepted")
        ProfileClaim.objects.create(
            profile=profile,
            claim_type="skill",
            text="Built Django APIs.",
            status="unconfirmed",
        )
        original_updated_at = profile.updated_at

        response = self.client.post(
            reverse("api_agent_runs"),
            data='{"agent_type": "profile_builder", "provider": "direct_api"}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["agent_type"], "profile_builder")
        self.assertEqual(payload["status"], "waiting_approval")
        self.assertIn("readiness score", payload["result_summary"].lower())
        self.assertTrue(payload["steps"])
        self.assertTrue(all(step["status"] != "running" for step in payload["steps"]))
        self.assertTrue(any(artifact["title"] == "Profile Builder Review" for artifact in payload["artifacts"]))
        self.assertTrue(payload["permissions"])
        self.assertTrue(payload["runtime_invocations"])
        self.assertTrue(payload["decisions"])
        self.assertTrue(payload["audit_logs"])
        self.assertNotIn("Python backend engineer", response.content.decode())
        profile.refresh_from_db()
        self.assertEqual(profile.updated_at, original_updated_at)

    def test_agent_run_cancel_and_retry(self):
        ensure_provider_settings()
        run = AgentRun.objects.create(
            agent_type="profile_builder",
            provider="direct_api",
            tool_policy="read_only",
            status="queued",
        )

        cancel_response = self.client.post(reverse("api_agent_run_cancel", args=[run.id]))

        self.assertEqual(cancel_response.status_code, 200)
        self.assertEqual(cancel_response.json()["status"], "cancelled")

        retry_response = self.client.post(reverse("api_agent_run_retry", args=[run.id]))

        self.assertEqual(retry_response.status_code, 201)
        self.assertNotEqual(retry_response.json()["id"], run.id)
        self.assertEqual(retry_response.json()["agent_type"], "profile_builder")
        self.assertIn(retry_response.json()["status"], {"success", "failed", "waiting_approval"})

    def test_agent_workflow_runs_create_reviewable_artifacts(self):
        profile = CandidateProfile.objects.create(full_name="Jane Dev", skills=["Python", "Django"], headline="Backend Engineer")
        TargetTitle.objects.create(profile=profile, title="Backend Engineer", status="accepted")
        company = Company.objects.create(name="Acme", careers_url="https://jobs.lever.co/acme", scraper_type="lever")
        job = Job.objects.create(
            company=company,
            title="Backend Engineer",
            location="Remote",
            description="Python Django APIs",
            apply_url="https://jobs.lever.co/acme/backend",
            source_url=company.careers_url,
            source_platform="lever",
            tags=["python", "django"],
        )
        application = Application.objects.create(job=job, status="saved", next_action="Tailor CV")
        ApplicationArtifact.objects.create(
            application=application,
            artifact_type="tailoring_plan",
            title="Tailoring Plan",
            content="Plan",
            status="approved",
        )

        for agent_type in ("match_review", "search_strategy", "application_prep", "follow_up"):
            response = self.client.post(
                reverse("api_agent_runs"),
                data=json.dumps({"agent_type": agent_type, "provider": "direct_api"}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 201)
            payload = response.json()
            self.assertEqual(payload["agent_type"], agent_type)
            self.assertEqual(payload["status"], "waiting_approval")
            self.assertTrue(payload["artifacts"])
            self.assertTrue(payload["decisions"])

    def test_agent_decision_accept_reject_is_review_only(self):
        CandidateProfile.objects.create(full_name="Jane Dev", skills=["Python"], cv_markdown="# CV")

        run_response = self.client.post(
            reverse("api_agent_runs"),
            data='{"agent_type": "profile_builder", "provider": "direct_api"}',
            content_type="application/json",
        )
        decision_id = run_response.json()["decisions"][0]["id"]
        approve_response = self.client.post(reverse("api_agent_decision_status", args=[decision_id, "approved"]))

        self.assertEqual(run_response.status_code, 201)
        self.assertEqual(approve_response.status_code, 200)
        self.assertEqual(approve_response.json()["status"], "approved")
        self.assertEqual(AgentDecision.objects.get(id=decision_id).status, "approved")
        self.assertEqual(AgentRun.objects.get(id=run_response.json()["id"]).status, "success")

    def test_analytics_feedback_post_persists_without_mutating_alert(self):
        company = Company.objects.create(name="Acme", careers_url="https://jobs.lever.co/acme", scraper_type="lever")
        job = Job.objects.create(
            company=company,
            title="Backend Engineer",
            location="Remote",
            apply_url="https://x/analytics-1",
            source_url=company.careers_url,
            source_platform="lever",
        )
        alert = JobAlert.objects.create(company=company, job=job, title="New role: Backend Engineer")

        response = self.client.post(
            reverse("api_analytics_feedback"),
            data='{"alert_id": %d, "rating": "relevant", "reason": "Strong stack match", "tags": "python, remote"}' % alert.id,
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["rating"], "relevant")
        self.assertEqual(payload["tags"], ["python", "remote"])
        alert.refresh_from_db()
        self.assertEqual(alert.status, "unread")
        self.assertEqual(AlertFeedback.objects.get(alert=alert).job, job)

    def test_analytics_overview_reports_source_quality_and_suggestions(self):
        company = Company.objects.create(
            name="NoisyCo",
            careers_url="https://jobs.lever.co/noisy",
            scraper_type="lever",
            source_health="active",
        )
        ScanJob.objects.create(company=company, status="success", jobs_found=2, jobs_created=2, source_platform="lever")
        ScanJob.objects.create(company=company, status="failed", message="Timeout", source_platform="lever")
        first_job = Job.objects.create(
            company=company,
            title="Salesforce Admin",
            location="Remote",
            apply_url="https://x/noisy-1",
            source_url=company.careers_url,
            source_platform="lever",
        )
        second_job = Job.objects.create(
            company=company,
            title="Salesforce Support Engineer",
            location="Remote",
            apply_url="https://x/noisy-2",
            source_url=company.careers_url,
            source_platform="lever",
        )
        first_alert = JobAlert.objects.create(company=company, job=first_job, title="New role: Salesforce Admin")
        second_alert = JobAlert.objects.create(company=company, job=second_job, title="New role: Salesforce Support Engineer")
        AlertFeedback.objects.create(alert=first_alert, job=first_job, company=company, rating="irrelevant")
        AlertFeedback.objects.create(alert=second_alert, job=second_job, company=company, rating="irrelevant")

        response = self.client.get(reverse("api_analytics"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreaterEqual(payload["summary"]["companies_tracked"], 1)
        self.assertEqual(payload["summary"]["feedback_irrelevant"], 2)
        noisy_metric = next(metric for metric in payload["company_metrics"] if metric["company_name"] == "NoisyCo")
        self.assertTrue(noisy_metric["noisy"])
        self.assertTrue(any(metric["source_platform"] == "lever" for metric in payload["platform_metrics"]))
        self.assertTrue(any(item["suggestion_type"] == "negative_keywords" for item in payload["filter_suggestions"]))
        self.assertIn("latest_weekly_review", payload)

    def test_weekly_review_generation_is_review_only(self):
        profile = CandidateProfile.objects.create(full_name="Jane Dev", skills=["Python"])
        TargetTitle.objects.create(profile=profile, title="Backend Engineer", status="accepted")
        company = Company.objects.create(name="Acme", careers_url="https://jobs.lever.co/acme", scraper_type="lever")
        job = Job.objects.create(
            company=company,
            title="Backend Engineer",
            location="Remote",
            description="Python APIs",
            apply_url="https://jobs.lever.co/acme/backend",
            source_url=company.careers_url,
            source_platform="lever",
            tags=["python"],
        )
        Application.objects.create(job=job, status="saved")

        response = self.client.post(reverse("api_analytics_weekly_review_generate"))
        overview_response = self.client.get(reverse("api_analytics"))

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["recommendations"])
        self.assertEqual(WeeklyReview.objects.count(), 1)
        self.assertIsNotNone(overview_response.json()["latest_weekly_review"])

    def test_export_includes_alert_feedback_without_secrets(self):
        company = Company.objects.create(name="Acme", careers_url="https://jobs.lever.co/acme", scraper_type="lever")
        job = Job.objects.create(
            company=company,
            title="Backend Engineer",
            location="Remote",
            apply_url="https://x/analytics-export",
            source_url=company.careers_url,
            source_platform="lever",
        )
        alert = JobAlert.objects.create(company=company, job=job, title="New role: Backend Engineer")
        AlertFeedback.objects.create(
            alert=alert,
            job=job,
            company=company,
            rating="maybe",
            reason="Needs salary check",
            tags=["salary"],
        )

        response = self.client.get(reverse("api_export"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("alert_feedback", payload)
        self.assertEqual(payload["alert_feedback"][0]["rating"], "maybe")

    def test_notification_preferences_get_and_update(self):
        response = self.client.get(reverse("api_notification_preferences"))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["quiet_hours_enabled"])
        self.assertEqual(response.json()["digest_frequency"], "daily")

        response = self.client.patch(
            reverse("api_notification_preferences"),
            data=(
                '{"quiet_hours_enabled": true, "quiet_hours_start": "21:30", '
                '"quiet_hours_end": "08:15", "timezone": "Asia/Kolkata", '
                '"digest_enabled": true, "digest_frequency": "weekdays", '
                '"digest_time": "09:45", "digest_channel": "local"}'
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["quiet_hours_enabled"])
        self.assertEqual(payload["quiet_hours_start"], "21:30")
        self.assertEqual(payload["quiet_hours_end"], "08:15")
        self.assertEqual(payload["timezone"], "Asia/Kolkata")
        self.assertTrue(payload["digest_enabled"])
        self.assertEqual(payload["digest_frequency"], "weekdays")
        self.assertEqual(NotificationPreference.objects.count(), 1)

    def test_notification_preferences_are_in_diagnostics_and_export(self):
        NotificationPreference.objects.create(
            quiet_hours_enabled=True,
            timezone="UTC",
            digest_enabled=True,
            digest_frequency="daily",
            digest_channel="local",
        )

        diagnostics_response = self.client.get(reverse("api_diagnostics"))
        export_response = self.client.get(reverse("api_export"))

        self.assertEqual(diagnostics_response.status_code, 200)
        self.assertEqual(diagnostics_response.json()["notifications"]["status"], "configured")
        self.assertEqual(export_response.status_code, 200)
        self.assertTrue(export_response.json()["notification_preferences"]["quiet_hours_enabled"])

    def test_jobs_list_includes_deterministic_match_and_sorts_strong_fit_first(self):
        profile = CandidateProfile.objects.create(
            full_name="Jane Dev",
            headline="Senior Backend Engineer",
            remote_preference="remote",
            target_locations=["Remote"],
            preferred_work_modes=["remote"],
            skills=["Python", "Django", "Postgres"],
            summary="Senior backend engineer.",
            cv_markdown="# CV",
        )
        TargetTitle.objects.create(profile=profile, title="Backend Engineer", status="accepted")
        company = Company.objects.create(name="Acme", careers_url="https://jobs.lever.co/acme", scraper_type="lever")
        weak_job = Job.objects.create(
            company=company,
            title="Sales Manager",
            location="Bengaluru, India",
            description="Own enterprise sales pipeline.",
            apply_url="https://x/match-weak",
            source_url=company.careers_url,
            source_platform="lever",
            remote_policy="onsite",
        )
        strong_job = Job.objects.create(
            company=company,
            title="Senior Backend Engineer",
            location="Remote, India",
            description="Build Python Django APIs backed by Postgres.",
            apply_url="https://x/match-strong",
            source_url=company.careers_url,
            source_platform="lever",
            remote_policy="remote",
            tags=["Python", "Django", "Postgres"],
        )

        response = self.client.get(reverse("api_jobs"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["results"][0]["id"], strong_job.id)
        self.assertGreater(payload["results"][0]["match"]["overall_score"], payload["results"][1]["match"]["overall_score"])
        self.assertEqual(payload["results"][0]["match"]["apply_priority"], "apply_now")
        self.assertTrue(payload["results"][0]["match"]["evidence"])
        self.assertEqual(JobMatch.objects.count(), 2)
        self.assertTrue(JobMatch.objects.filter(job=weak_job).exists())

    def test_match_score_correction_adjusts_and_can_be_undone(self):
        profile = CandidateProfile.objects.create(
            full_name="Jane Dev",
            headline="Backend Engineer",
            skills=["Python", "Django"],
            remote_preference="remote",
        )
        TargetTitle.objects.create(profile=profile, title="Backend Engineer", status="accepted")
        company = Company.objects.create(name="Acme", careers_url="https://jobs.lever.co/acme", scraper_type="lever")
        job = Job.objects.create(
            company=company,
            title="Backend Engineer",
            location="Remote",
            description="Python Django APIs",
            apply_url="https://x/match-correction",
            source_url=company.careers_url,
            source_platform="lever",
            remote_policy="remote",
        )
        original_score = refresh_job_match(job).overall_score

        correction_response = self.client.post(
            reverse("api_analytics_match_corrections"),
            data=json.dumps({"job_id": job.id, "correction": "too_high", "reason": "Seems less relevant after reading"}),
            content_type="application/json",
        )
        job.refresh_from_db()
        lowered_score = refresh_job_match(job).overall_score
        learning_change_id = correction_response.json()["correction"]["learning_change_id"]
        undo_response = self.client.post(reverse("api_analytics_learning_change_undo", args=[learning_change_id]))
        restored_score = refresh_job_match(job).overall_score

        self.assertEqual(correction_response.status_code, 201)
        self.assertLess(lowered_score, original_score)
        self.assertEqual(MatchScoreCorrection.objects.count(), 1)
        self.assertEqual(LearningChange.objects.count(), 1)
        self.assertEqual(undo_response.status_code, 200)
        self.assertEqual(undo_response.json()["status"], "undone")
        self.assertEqual(restored_score, original_score)

    def test_jobs_list_match_works_without_profile(self):
        company = Company.objects.create(name="Acme", careers_url="https://jobs.lever.co/acme", scraper_type="lever")
        Job.objects.create(
            company=company,
            title="Backend Engineer",
            location="Remote, India",
            description="Build APIs.",
            apply_url="https://x/match-no-profile",
            source_url=company.careers_url,
            source_platform="lever",
            remote_policy="remote",
        )

        response = self.client.get(reverse("api_jobs"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 1)
        self.assertIn("No profile is available", " ".join(payload["results"][0]["match"]["reasons_to_skip"]))

    def test_export_includes_job_matches(self):
        company = Company.objects.create(name="Acme", careers_url="https://jobs.lever.co/acme", scraper_type="lever")
        job = Job.objects.create(
            company=company,
            title="Backend Engineer",
            location="Remote",
            description="Build APIs.",
            apply_url="https://x/match-export",
            source_url=company.careers_url,
            source_platform="lever",
            remote_policy="remote",
        )
        JobMatch.objects.create(job=job, overall_score=75, confidence_score=50, apply_priority="consider")

        response = self.client.get(reverse("api_export"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("job_matches", payload)
        self.assertGreaterEqual(len(payload["job_matches"]), 1)
        self.assertIn("overall_score", payload["job_matches"][0])
