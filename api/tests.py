from django.test import TestCase
from django.urls import reverse

from companies.models import Company
from jobs.models import Job


class ApiTests(TestCase):
    def test_health(self):
        response = self.client.get(reverse("api_health"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_companies_post_json(self):
        response = self.client.post(
            reverse("api_companies"),
            data='{"careers_url": "https://boards.greenhouse.io/acme", "name": "Acme"}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Company.objects.get(careers_url="https://boards.greenhouse.io/acme").scraper_type, "greenhouse")

    def test_jobs_list(self):
        company = Company.objects.create(name="Acme", careers_url="https://jobs.lever.co/acme", scraper_type="lever")
        Job.objects.create(company=company, title="Frontend Engineer", apply_url="https://x/1", source_url=company.careers_url, source_platform="lever", tags=["react"])

        response = self.client.get(reverse("api_jobs"), {"tech": "react"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
