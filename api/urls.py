from django.urls import path

from . import views


urlpatterns = [
    path("health", views.health, name="api_health"),
    path("jobs", views.jobs_list, name="api_jobs"),
    path("jobs/<int:job_id>", views.job_detail, name="api_job_detail"),
    path("companies", views.companies_list, name="api_companies"),
    path("companies/<int:company_id>/scrape", views.company_scrape, name="api_company_scrape"),
]
