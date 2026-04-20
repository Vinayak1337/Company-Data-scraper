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
    if url:
        create_company_from_url(url, name)
    if request.headers.get("HX-Request"):
        return render(request, "dashboard/partials/company_panel.html", base_context(request))
    return redirect("dashboard")


@require_POST
def scrape_company(request: HttpRequest, company_id: int) -> HttpResponse:
    company = get_object_or_404(Company, pk=company_id)
    scrape_company_jobs(company)
    if request.headers.get("HX-Request"):
        return render(request, "dashboard/partials/dashboard_content.html", base_context(request))
    return redirect("dashboard")


@require_POST
def delete_company(request: HttpRequest, company_id: int) -> HttpResponse:
    get_object_or_404(Company, pk=company_id).delete()
    if request.headers.get("HX-Request"):
        return render(request, "dashboard/partials/company_panel.html", base_context(request))
    return redirect("dashboard")


@require_GET
def jobs_partial(request: HttpRequest) -> HttpResponse:
    return render(request, "dashboard/partials/jobs_table.html", base_context(request))


@require_GET
def job_detail_partial(request: HttpRequest, job_id: int) -> HttpResponse:
    job = get_object_or_404(Job.objects.select_related("company"), pk=job_id)
    return render(request, "dashboard/partials/job_detail.html", {"selected_job": job})


def base_context(request: HttpRequest) -> dict:
    filters = normalized_filters(request.GET)
    return {
        "stats": dashboard_stats(),
        "companies": company_counts(),
        "jobs": filter_jobs(request.GET),
        "tags": tag_cloud(),
        "india_states": INDIA_STATE_CHOICES,
        "india_cities": INDIA_CITY_CHOICES,
        "recent_logs": ScrapeLog.objects.select_related("company")[:5],
        "filters": filters,
    }
