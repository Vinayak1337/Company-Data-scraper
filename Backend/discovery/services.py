from __future__ import annotations

from urllib.parse import urlsplit

from django.db import IntegrityError, transaction

from companies.services import create_company_from_url, infer_name_from_url, validate_public_careers_url
from discovery.models import ManualUrlInboxItem
from jobs.models import Job


VALID_ITEM_TYPES = {choice[0] for choice in ManualUrlInboxItem.ITEM_TYPE_CHOICES}


def create_manual_url_item(url: str, item_type: str = "unknown", title: str = "", notes: str = "") -> ManualUrlInboxItem:
    url = validate_public_careers_url(url)
    item_type = normalize_item_type(item_type, url)
    title = str(title or "").strip()[:255]
    notes = str(notes or "").strip()[:5000]
    inferred_company = infer_name_from_url(url)

    try:
        item, created = ManualUrlInboxItem.objects.get_or_create(
            url=url,
            defaults={
                "item_type": item_type,
                "title": title,
                "notes": notes,
                "inferred_company": inferred_company,
            },
        )
    except IntegrityError:
        item = ManualUrlInboxItem.objects.get(url=url)
        created = False

    update_fields = []
    if not created and item.status == "dismissed":
        item.status = "pending"
        item.dismissed_at = None
        update_fields.extend(["status", "dismissed_at"])
    if not created and title and item.title != title:
        item.title = title
        update_fields.append("title")
    if not created and notes and item.notes != notes:
        item.notes = notes
        update_fields.append("notes")
    if not created and item.item_type == "unknown" and item_type != "unknown":
        item.item_type = item_type
        update_fields.append("item_type")
    if update_fields:
        item.save(update_fields=[*update_fields, "updated_at"])
    return item


@transaction.atomic
def import_manual_url_item(item: ManualUrlInboxItem) -> ManualUrlInboxItem:
    if item.status == "imported":
        return item

    if item.item_type == "company":
        company = create_company_from_url(item.url, item.title or item.inferred_company)
        item.mark_imported(company=company)
        return item

    if item.item_type == "job":
        company = company_for_job_url(item.url, item.inferred_company)
        job, _ = Job.objects.get_or_create(
            company=company,
            apply_url=item.url,
            defaults={
                "title": item.title or "Manual URL",
                "location": "",
                "description": item.notes,
                "source_url": item.url,
                "source_platform": "manual",
                "remote_policy": "unknown",
            },
        )
        item.mark_imported(company=company, job=job)
        return item

    raise ValueError("Choose company or job before importing this URL")


def dismiss_manual_url_item(item: ManualUrlInboxItem) -> ManualUrlInboxItem:
    item.dismiss()
    return item


def normalize_item_type(item_type: str, url: str) -> str:
    item_type = str(item_type or "unknown").strip().lower()
    if item_type in {"company", "job"}:
        return item_type
    parsed = urlsplit(url)
    path = parsed.path.casefold()
    if any(segment in path for segment in ("/jobs/", "/job/", "/positions/", "/position/", "/openings/")):
        return "job"
    if item_type in VALID_ITEM_TYPES:
        return item_type
    return "unknown"


def company_for_job_url(url: str, fallback_name: str = ""):
    parsed = urlsplit(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    return create_company_from_url(base_url, fallback_name or infer_name_from_url(base_url))
