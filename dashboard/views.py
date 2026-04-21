import json

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from companies.models import Company, ScrapeLog
from jobs.models import Job

from .services import (
    INDIA_CITY_CHOICES,
    INDIA_STATE_CHOICES,
    company_counts,
    create_company_from_url,
    dashboard_stats,
    filter_jobs,
    normalized_filters,
    reset_all_jobs,
    scrape_company_jobs,
    tag_cloud,
)


def dashboard(request: HttpRequest) -> HttpResponse:
    context = base_context(request)
    context["selected_job"] = None
    return render(request, "dashboard/index.html", context)


@require_POST
def add_company(request: HttpRequest) -> HttpResponse:
    url = request.POST.get("careers_url", "").strip()
    name = request.POST.get("name", "").strip()
    created = False
    if url:
        company = create_company_from_url(url, name)
        created = bool(company)
    if request.headers.get("HX-Request"):
        response = render(request, "dashboard/partials/company_panel.html", base_context(request))
        if created:
            _attach_toast(response, "success", "Company added. Click Scrape to pull jobs.")
        return response
    return redirect("dashboard")


@require_POST
def scrape_company(request: HttpRequest, company_id: int) -> HttpResponse:
    company = get_object_or_404(Company, pk=company_id)
    log = scrape_company_jobs(company)
    if request.headers.get("HX-Request"):
        response = render(request, "dashboard/partials/dashboard_content.html", base_context(request))
        if log.status == "success":
            _attach_toast(
                response,
                "success",
                f"{company.name}: {log.jobs_created} new, {log.jobs_updated} updated.",
            )
        else:
            _attach_toast(response, "error", f"{company.name}: scrape failed. {log.message[:120]}")
        return response
    return redirect("dashboard")


@require_POST
def delete_company(request: HttpRequest, company_id: int) -> HttpResponse:
    company = get_object_or_404(Company, pk=company_id)
    name = company.name
    company.delete()
    if request.headers.get("HX-Request"):
        response = render(request, "dashboard/partials/company_panel.html", base_context(request))
        _attach_toast(response, "success", f"Removed {name}.")
        return response
    return redirect("dashboard")


@require_POST
def reset_jobs(request: HttpRequest) -> HttpResponse:
    result = reset_all_jobs()
    if request.headers.get("HX-Request"):
        response = render(request, "dashboard/partials/dashboard_content.html", base_context(request))
        _attach_toast(
            response,
            "success",
            f"Cleared {result['jobs']} jobs and {result['logs']} scrape logs. Companies preserved.",
        )
        return response
    return redirect("dashboard")


@require_GET
def jobs_partial(request: HttpRequest) -> HttpResponse:
    return render(request, "dashboard/partials/jobs_table.html", base_context(request))


@require_GET
def job_detail_partial(request: HttpRequest, job_id: int) -> HttpResponse:
    job = get_object_or_404(Job.objects.select_related("company"), pk=job_id)
    return render(request, "dashboard/partials/job_detail.html", {"selected_job": job})


def base_context(request: HttpRequest) -> dict:
    params = request.GET if request.method == "GET" else request.POST
    filters = normalized_filters(params)
    jobs = list(filter_jobs(params))  # evaluate once — avoids double DB hit
    stats = dashboard_stats()
    # India is the default scope, so it alone doesn't count as an "active" filter
    has_active_filters = any([
        filters["q"],
        filters["title"],
        filters["company"],
        filters["state"],
        filters["city"],
        filters["location"],
        filters["tech"],
        filters["remote"],
        filters["country"] == "global",  # explicit switch to global is active
    ])
    return {
        "stats": stats,
        "companies": company_counts(),
        "jobs": jobs,
        "visible_count": len(jobs),
        "total_count": stats["total_jobs"],
        "tags": tag_cloud(),
        "india_states": INDIA_STATE_CHOICES,
        "india_cities": INDIA_CITY_CHOICES,
        "recent_logs": ScrapeLog.objects.select_related("company")[:5],
        "filters": filters,
        "has_active_filters": has_active_filters,
    }


def _attach_toast(response: HttpResponse, kind: str, message: str) -> None:
    response["HX-Trigger"] = json.dumps({"toast": {"type": kind, "msg": message}})
