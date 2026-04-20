import json

from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from companies.models import Company
from dashboard.services import create_company_from_url, filter_jobs, scrape_company_jobs
from jobs.models import Job


@require_GET
def health(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "ok"})


@require_GET
def jobs_list(request: HttpRequest) -> JsonResponse:
    jobs = [serialize_job(job) for job in filter_jobs(request.GET).select_related("company")[:200]]
    return JsonResponse({"count": len(jobs), "results": jobs})


@require_GET
def job_detail(request: HttpRequest, job_id: int) -> JsonResponse:
    return JsonResponse(serialize_job(get_object_or_404(Job.objects.select_related("company"), pk=job_id)))


@csrf_exempt
@require_http_methods(["GET", "POST"])
def companies_list(request: HttpRequest) -> JsonResponse:
    if request.method == "POST":
        payload = parse_json(request)
        url = payload.get("careers_url") or request.POST.get("careers_url", "")
        name = payload.get("name") or request.POST.get("name", "")
        if not url:
            return JsonResponse({"error": "careers_url is required"}, status=400)
        company = create_company_from_url(url.strip(), name.strip())
        return JsonResponse(serialize_company(company), status=201)
    companies = [serialize_company(company) for company in Company.objects.all()]
    return JsonResponse({"count": len(companies), "results": companies})


@csrf_exempt
@require_http_methods(["POST"])
def company_scrape(request: HttpRequest, company_id: int) -> JsonResponse:
    company = get_object_or_404(Company, pk=company_id)
    log = scrape_company_jobs(company)
    return JsonResponse(
        {
            "status": log.status,
            "message": log.message,
            "jobs_found": log.jobs_found,
            "jobs_created": log.jobs_created,
            "jobs_updated": log.jobs_updated,
        },
        status=200 if log.status == "success" else 500,
    )


def parse_json(request: HttpRequest) -> dict:
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return {}


def serialize_company(company: Company) -> dict:
    return {
        "id": company.id,
        "name": company.name,
        "careers_url": company.careers_url,
        "scraper_type": company.scraper_type,
        "is_active": company.is_active,
        "last_scraped_at": company.last_scraped_at.isoformat() if company.last_scraped_at else None,
        "last_scrape_status": company.last_scrape_status,
        "last_scrape_message": company.last_scrape_message,
    }


def serialize_job(job: Job) -> dict:
    return {
        "id": job.id,
        "title": job.title,
        "company": job.company.name,
        "company_id": job.company_id,
        "location": job.location,
        "description": job.description,
        "apply_url": job.apply_url,
        "source_url": job.source_url,
        "source_platform": job.source_platform,
        "external_id": job.external_id,
        "posted_at": job.posted_at.isoformat() if job.posted_at else None,
        "tags": job.tags,
        "remote_policy": job.remote_policy,
        "first_seen_at": job.first_seen_at.isoformat(),
        "last_seen_at": job.last_seen_at.isoformat(),
    }
