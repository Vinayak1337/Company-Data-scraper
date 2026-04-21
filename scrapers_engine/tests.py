from django.test import SimpleTestCase

from scrapers_engine import detect_scraper
from scrapers_engine.adapters import GenericScraper


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
