from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from companies.models import Company
from jobs.models import Job
from scrapers_engine import NormalizedJob, ScrapeResult


class DashboardTests(TestCase):
    def test_add_company_detects_scraper(self):
        response = self.client.post(reverse("add_company"), {"careers_url": "https://jobs.lever.co/acme"})

        self.assertEqual(response.status_code, 302)
        company = Company.objects.get(careers_url="https://jobs.lever.co/acme")
        self.assertEqual(company.scraper_type, "lever")

    def test_jobs_filter_by_title(self):
        company = Company.objects.create(name="Acme", careers_url="https://jobs.lever.co/acme", scraper_type="lever")
        Job.objects.create(company=company, title="Backend Engineer", location="Bengaluru, India", apply_url="https://x/1", source_url=company.careers_url, source_platform="lever")
        Job.objects.create(company=company, title="Product Designer", location="Bengaluru, India", apply_url="https://x/2", source_url=company.careers_url, source_platform="lever")

        response = self.client.get(reverse("jobs_partial"), {"title": "backend"})

        self.assertContains(response, "Backend Engineer")
        self.assertNotContains(response, "Product Designer")

    def test_jobs_default_to_india_scope(self):
        company = Company.objects.create(name="Acme", careers_url="https://jobs.lever.co/acme", scraper_type="lever")
        Job.objects.create(company=company, title="India Role", location="New Delhi, DL,IN, IN", apply_url="https://x/1", source_url=company.careers_url, source_platform="lever")
        Job.objects.create(company=company, title="US Role", location="San Francisco, CA", apply_url="https://x/2", source_url=company.careers_url, source_platform="lever")

        response = self.client.get(reverse("jobs_partial"))

        self.assertContains(response, "India Role")
        self.assertNotContains(response, "US Role")

    def test_jobs_can_filter_india_city(self):
        company = Company.objects.create(name="Acme", careers_url="https://jobs.lever.co/acme", scraper_type="lever")
        Job.objects.create(company=company, title="Delhi Role", location="New Delhi, DL,IN, IN", apply_url="https://x/1", source_url=company.careers_url, source_platform="lever")
        Job.objects.create(company=company, title="Bengaluru Role", location="Bengaluru, India", apply_url="https://x/2", source_url=company.careers_url, source_platform="lever")

        response = self.client.get(reverse("jobs_partial"), {"city": "Delhi"})

        self.assertContains(response, "Delhi Role")
        self.assertNotContains(response, "Bengaluru Role")

    @patch("dashboard.services.scrape")
    def test_scrape_company_upserts_jobs(self, mock_scrape):
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
                    tags=["python", "django"],
                    remote_policy="remote",
                )
            ],
        )

        response = self.client.post(reverse("scrape_company", args=[company.id]))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Job.objects.count(), 1)
        company.refresh_from_db()
        self.assertEqual(company.last_scrape_status, "success")
