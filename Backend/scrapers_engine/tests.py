from django.test import SimpleTestCase

from scrapers_engine import detect_scraper
from scrapers_engine.adapters import GenericScraper, is_probable_job


class ScraperDetectionTests(SimpleTestCase):
    def test_detect_known_platforms(self):
        self.assertEqual(detect_scraper("https://boards.greenhouse.io/acme"), "greenhouse")
        self.assertEqual(detect_scraper("https://jobs.lever.co/acme"), "lever")
        self.assertEqual(detect_scraper("https://jobs.ashbyhq.com/acme"), "ashby")
        self.assertEqual(detect_scraper("https://apply.careers.microsoft.com/careers?pid=123"), "microsoft")
        self.assertEqual(detect_scraper("https://example.com/careers"), "generic")

    def test_generic_remote_policy(self):
        scraper = GenericScraper()

        self.assertEqual(scraper.infer_remote_policy("Senior Engineer Remote"), "remote")

    def test_generic_parser_rejects_navigation_links(self):
        self.assertFalse(is_probable_job("Home", "https://example.com/careers/jobs/123456"))
        self.assertFalse(is_probable_job("Teams", "https://example.com/careers/teams"))
        self.assertFalse(is_probable_job("English", "https://example.com/careers/jobs"))
        self.assertFalse(is_probable_job("Job Search", "https://example.com/jobs/search"))

    def test_generic_parser_accepts_real_role_titles(self):
        self.assertTrue(is_probable_job("Backend Platform Engineer", "https://example.com/careers/jobs/123456"))
        self.assertTrue(is_probable_job("Staff Product Manager", "https://example.com/openings/staff-product-manager"))
