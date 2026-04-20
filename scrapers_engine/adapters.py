import re
from datetime import datetime
from html import unescape
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from django.conf import settings

from .core import NormalizedJob, ScrapeResult, hostname


TECH_TERMS = {
    "python", "django", "flask", "fastapi", "javascript", "typescript", "react", "vue", "angular",
    "node", "node.js", "java", "spring", "go", "golang", "rust", "ruby", "rails", "php", "laravel",
    "aws", "azure", "gcp", "kubernetes", "docker", "terraform", "sql", "postgres", "mysql",
    "redis", "graphql", "machine learning", "ml", "ai", "data", "spark",
}


class BaseScraper:
    source_platform = "generic"

    def can_handle(self, url: str) -> bool:
        return False

    def get(self, url: str) -> requests.Response:
        response = requests.get(
            url,
            headers={"User-Agent": settings.SCRAPER_USER_AGENT, "Accept": "text/html,application/json"},
            timeout=settings.SCRAPER_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response

    def infer_company_name(self, url: str, fallback: str = "") -> str:
        host = hostname(url).replace("www.", "")
        if fallback:
            return clean_text(fallback)
        parts = host.split(".")
        return parts[-2].replace("-", " ").title() if len(parts) >= 2 else host.title()

    def infer_remote_policy(self, text: str) -> str:
        lowered = text.lower()
        if "hybrid" in lowered:
            return "hybrid"
        if "remote" in lowered or "work from anywhere" in lowered:
            return "remote"
        if "onsite" in lowered or "on-site" in lowered or "office" in lowered:
            return "onsite"
        return "unknown"

    def infer_tags(self, text: str) -> list[str]:
        lowered = text.lower()
        found = sorted(term for term in TECH_TERMS if re.search(rf"\b{re.escape(term)}\b", lowered))
        return found[:12]


class GreenhouseScraper(BaseScraper):
    source_platform = "greenhouse"

    def can_handle(self, url: str) -> bool:
        host = hostname(url)
        return "greenhouse.io" in host or "greenhouse.com" in host

    def scrape(self, url: str) -> ScrapeResult:
        board_token = greenhouse_board_token(url)
        if board_token:
            api_url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"
            data = self.get(api_url).json()
            company_name = self.infer_company_name(url, data.get("name", ""))
            jobs = [
                NormalizedJob(
                    title=clean_text(item.get("title", "")),
                    company_name=company_name,
                    location=clean_text((item.get("location") or {}).get("name", "")),
                    description=html_to_text(item.get("content", "")),
                    apply_url=item.get("absolute_url") or url,
                    source_url=url,
                    source_platform=self.source_platform,
                    external_id=str(item.get("id") or ""),
                    posted_at=parse_datetime(item.get("updated_at")),
                    tags=self.infer_tags(f"{item.get('title', '')} {item.get('content', '')}"),
                    remote_policy=self.infer_remote_policy(f"{item.get('title', '')} {(item.get('location') or {}).get('name', '')} {item.get('content', '')}"),
                )
                for item in data.get("jobs", [])
                if item.get("title")
            ]
            return ScrapeResult(self.source_platform, company_name, jobs)
        return GenericScraper().scrape(url)


class LeverScraper(BaseScraper):
    source_platform = "lever"

    def can_handle(self, url: str) -> bool:
        return "lever.co" in hostname(url)

    def scrape(self, url: str) -> ScrapeResult:
        company = lever_company_slug(url)
        api_url = f"https://api.lever.co/v0/postings/{company}?mode=json"
        data = self.get(api_url).json()
        company_name = self.infer_company_name(url, company)
        jobs = []
        for item in data:
            categories = item.get("categories") or {}
            text = " ".join([
                item.get("text", ""),
                categories.get("location", ""),
                categories.get("team", ""),
                categories.get("commitment", ""),
                item.get("descriptionPlain", ""),
            ])
            jobs.append(
                NormalizedJob(
                    title=clean_text(item.get("text", "")),
                    company_name=company_name,
                    location=clean_text(categories.get("location", "")),
                    description=clean_text(item.get("descriptionPlain", "")),
                    apply_url=item.get("hostedUrl") or item.get("applyUrl") or url,
                    source_url=url,
                    source_platform=self.source_platform,
                    external_id=str(item.get("id") or ""),
                    posted_at=parse_timestamp_ms(item.get("createdAt")),
                    tags=self.infer_tags(text),
                    remote_policy=self.infer_remote_policy(text),
                )
            )
        return ScrapeResult(self.source_platform, company_name, jobs)


class AshbyScraper(BaseScraper):
    source_platform = "ashby"

    def can_handle(self, url: str) -> bool:
        return "ashbyhq.com" in hostname(url)

    def scrape(self, url: str) -> ScrapeResult:
        response = self.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        company_name = self.infer_company_name(url, ashby_company_slug(url))
        jobs = []
        for link in soup.select("a[href*='/jobs/']"):
            title = clean_text(link.get_text(" ", strip=True))
            href = urljoin(url, link.get("href", ""))
            if title and href:
                text = f"{title} {href}"
                jobs.append(
                    NormalizedJob(
                        title=title,
                        company_name=company_name,
                        location="",
                        description="",
                        apply_url=href,
                        source_url=url,
                        source_platform=self.source_platform,
                        external_id=href.rstrip("/").split("/")[-1],
                        tags=self.infer_tags(text),
                        remote_policy=self.infer_remote_policy(text),
                    )
                )
        return ScrapeResult(self.source_platform, company_name, dedupe_jobs(jobs))


class GenericScraper(BaseScraper):
    source_platform = "generic"

    def can_handle(self, url: str) -> bool:
        return True

    def scrape(self, url: str) -> ScrapeResult:
        response = self.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.find("title")
        company_name = self.infer_company_name(url, title.get_text(" ", strip=True) if title else "")
        jobs = []
        selectors = [
            "a[href*='job']",
            "a[href*='career']",
            "[class*='job'] a",
            "[class*='opening'] a",
            "[data-job-id]",
        ]
        for element in soup.select(",".join(selectors)):
            link = element if element.name == "a" else element.find("a")
            if not link:
                continue
            href = urljoin(url, link.get("href", ""))
            text = clean_text(link.get_text(" ", strip=True))
            if not is_probable_job(text, href):
                continue
            parent_text = clean_text((element.parent or element).get_text(" ", strip=True))
            jobs.append(
                NormalizedJob(
                    title=text[:255],
                    company_name=company_name,
                    location=infer_location(parent_text),
                    description=parent_text,
                    apply_url=href,
                    source_url=url,
                    source_platform=self.source_platform,
                    external_id=href.rstrip("/").split("/")[-1],
                    tags=self.infer_tags(parent_text),
                    remote_policy=self.infer_remote_policy(parent_text),
                )
            )
        return ScrapeResult(self.source_platform, company_name, dedupe_jobs(jobs))


def greenhouse_board_token(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    if query.get("for"):
        return query["for"][0]
    parts = [part for part in parsed.path.split("/") if part]
    for marker in ("embed/job_board", "boards"):
        if marker in parsed.path and parts:
            return parts[-1]
    if "boards.greenhouse.io" in parsed.netloc and parts:
        return parts[0]
    return ""


def lever_company_slug(url: str) -> str:
    parts = [part for part in urlparse(url).path.split("/") if part]
    return parts[0] if parts else hostname(url).split(".")[0]


def ashby_company_slug(url: str) -> str:
    parts = [part for part in urlparse(url).path.split("/") if part]
    return parts[-1] if parts else hostname(url).split(".")[0]


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def parse_timestamp_ms(value: int | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromtimestamp(value / 1000)


def html_to_text(value: str) -> str:
    return clean_text(BeautifulSoup(unescape(value or ""), "html.parser").get_text(" ", strip=True))


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def is_probable_job(title: str, href: str) -> bool:
    if len(title) < 4 or len(title) > 180:
        return False
    lowered = f"{title} {href}".lower()
    noisy = ("privacy", "cookie", "terms", "login", "signup", "blog", "press")
    return ("job" in lowered or "career" in lowered or "opening" in lowered or "apply" in lowered) and not any(term in lowered for term in noisy)


def infer_location(text: str) -> str:
    candidates = ["Remote", "Hybrid", "New York", "San Francisco", "London", "Bengaluru", "Bangalore", "India", "United States"]
    lowered = text.lower()
    for candidate in candidates:
        if candidate.lower() in lowered:
            return candidate
    return ""


def dedupe_jobs(jobs: list[NormalizedJob]) -> list[NormalizedJob]:
    seen = set()
    unique = []
    for job in jobs:
        key = job.apply_url or f"{job.title}:{job.location}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(job)
    return unique


SCRAPERS = [GreenhouseScraper(), LeverScraper(), AshbyScraper()]
