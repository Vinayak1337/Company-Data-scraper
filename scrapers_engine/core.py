from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol
from urllib.parse import urlparse


@dataclass
class NormalizedJob:
    title: str
    company_name: str
    location: str
    description: str
    apply_url: str
    source_url: str
    source_platform: str
    external_id: str = ""
    posted_at: datetime | None = None
    tags: list[str] = field(default_factory=list)
    remote_policy: str = "unknown"


@dataclass
class ScrapeResult:
    source_platform: str
    company_name: str
    jobs: list[NormalizedJob]


class Scraper(Protocol):
    source_platform: str

    def can_handle(self, url: str) -> bool:
        ...

    def scrape(self, url: str) -> ScrapeResult:
        ...


def detect_scraper(url: str) -> str:
    from .adapters import SCRAPERS

    for scraper in SCRAPERS:
        if scraper.can_handle(url):
            return scraper.source_platform
    return "generic"


def scrape(url: str) -> ScrapeResult:
    from .adapters import SCRAPERS, GenericScraper

    for scraper in SCRAPERS:
        if scraper.can_handle(url):
            return scraper.scrape(url)
    return GenericScraper().scrape(url)


def hostname(url: str) -> str:
    return urlparse(url).hostname or ""
