from django.urls import path

from . import views


urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("companies/add/", views.add_company, name="add_company"),
    path("companies/<int:company_id>/scrape/", views.scrape_company, name="scrape_company"),
    path("companies/<int:company_id>/delete/", views.delete_company, name="delete_company"),
    path("jobs/", views.jobs_partial, name="jobs_partial"),
    path("jobs/reset/", views.reset_jobs, name="reset_jobs"),
    path("jobs/<int:job_id>/detail/", views.job_detail_partial, name="job_detail_partial"),
]
