from datetime import datetime, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from notifications.models import NotificationEvent, NotificationPreference


def get_notification_preferences() -> NotificationPreference:
    preference = NotificationPreference.objects.order_by("id").first()
    if preference:
        return preference
    return NotificationPreference.objects.create()


def update_notification_preferences(preference: NotificationPreference, updates: dict) -> NotificationPreference:
    update_fields = []
    bool_fields = ("quiet_hours_enabled", "digest_enabled", "immediate_email_enabled")
    time_fields = ("quiet_hours_start", "quiet_hours_end", "digest_time")

    for field in bool_fields:
        if field in updates:
            value = coerce_bool(updates[field])
            if getattr(preference, field) != value:
                setattr(preference, field, value)
                update_fields.append(field)

    for field in time_fields:
        if field in updates:
            value = coerce_time(updates[field], field)
            if getattr(preference, field) != value:
                setattr(preference, field, value)
                update_fields.append(field)

    if "timezone" in updates:
        value = str(updates["timezone"] or "UTC").strip() or "UTC"
        validate_timezone(value)
        if preference.timezone != value:
            preference.timezone = value
            update_fields.append("timezone")

    if "digest_frequency" in updates:
        value = str(updates["digest_frequency"] or "").strip()
        validate_choice(value, {choice[0] for choice in NotificationPreference.DIGEST_FREQUENCY_CHOICES}, "digest_frequency")
        if preference.digest_frequency != value:
            preference.digest_frequency = value
            update_fields.append("digest_frequency")

    if "digest_channel" in updates:
        value = str(updates["digest_channel"] or "").strip()
        validate_choice(value, {choice[0] for choice in NotificationPreference.DIGEST_CHANNEL_CHOICES}, "digest_channel")
        if preference.digest_channel != value:
            preference.digest_channel = value
            update_fields.append("digest_channel")

    if "email_address" in updates:
        value = str(updates["email_address"] or "").strip()
        if preference.email_address != value:
            preference.email_address = value
            update_fields.append("email_address")

    for field in ("minimum_match_score", "minimum_confidence_score", "max_digest_items"):
        if field in updates:
            value = positive_int(updates[field], field)
            if getattr(preference, field) != value:
                setattr(preference, field, value)
                update_fields.append(field)

    if update_fields:
        preference.save(update_fields=[*update_fields, "updated_at"])
    return preference


def serialize_notification_preferences(preference: NotificationPreference) -> dict:
    return {
        "id": preference.id,
        "quiet_hours_enabled": preference.quiet_hours_enabled,
        "quiet_hours_start": format_time(preference.quiet_hours_start),
        "quiet_hours_end": format_time(preference.quiet_hours_end),
        "timezone": preference.timezone,
        "quiet_hours_active": quiet_hours_active(preference),
        "digest_enabled": preference.digest_enabled,
        "digest_frequency": preference.digest_frequency,
        "digest_time": format_time(preference.digest_time),
        "digest_channel": preference.digest_channel,
        "email_address": preference.email_address,
        "immediate_email_enabled": preference.immediate_email_enabled,
        "minimum_match_score": preference.minimum_match_score,
        "minimum_confidence_score": preference.minimum_confidence_score,
        "max_digest_items": preference.max_digest_items,
        "created_at": preference.created_at.isoformat() if preference.created_at else None,
        "updated_at": preference.updated_at.isoformat() if preference.updated_at else None,
    }


def notification_preferences_status(preference: NotificationPreference | None = None) -> dict:
    preference = preference or get_notification_preferences()
    configured = bool(
        (preference.digest_enabled or preference.immediate_email_enabled)
        and (preference.digest_channel == "local" or preference.email_address)
    )
    return {
        "status": "configured" if configured else "not_configured",
        "configured": configured,
        "quiet_hours_enabled": preference.quiet_hours_enabled,
        "quiet_hours_active": quiet_hours_active(preference),
        "digest_enabled": preference.digest_enabled,
        "digest_frequency": preference.digest_frequency,
        "digest_channel": preference.digest_channel,
        "email_address": preference.email_address,
        "minimum_match_score": preference.minimum_match_score,
        "minimum_confidence_score": preference.minimum_confidence_score,
        "timezone": preference.timezone,
    }


def create_notification_event(match, channel: str | None = None) -> NotificationEvent:
    preference = get_notification_preferences()
    selected_channel = channel or ("email" if preference.digest_channel == "email" else "local")
    job = match.job
    idempotency_key = f"{selected_channel}-job-{job.id}-match-{match.id}-{match.overall_score}-{match.confidence_score}"
    event, _ = NotificationEvent.objects.get_or_create(
        idempotency_key=idempotency_key,
        defaults={
            "job": job,
            "match": match,
            "channel": selected_channel,
            "status": "queued",
            "subject": f"{match.overall_score}% match: {job.title} at {job.company.name}",
            "body": notification_body(match),
            "score_at_send": match.overall_score,
            "confidence_at_send": match.confidence_score,
        },
    )
    if selected_channel == "email" and preference.immediate_email_enabled:
        send_notification_event(event, preference=preference)
    return event


def send_queued_notification_events(limit: int = 25) -> dict:
    preference = get_notification_preferences()
    events = NotificationEvent.objects.filter(channel="email", status="queued").select_related("job", "match").order_by("created_at")[: max(limit, 0)]
    sent = 0
    skipped = 0
    failed = 0
    for event in events:
        before = event.status
        send_notification_event(event, preference=preference)
        event.refresh_from_db()
        if event.status == "sent":
            sent += 1
        elif event.status == "failed":
            failed += 1
        elif before == event.status:
            skipped += 1
    return {"sent": sent, "skipped": skipped, "failed": failed}


def send_notification_event(event: NotificationEvent, preference: NotificationPreference | None = None) -> NotificationEvent:
    preference = preference or get_notification_preferences()
    if event.channel != "email":
        return event
    if event.status == "sent":
        return event
    if not preference.email_address:
        event.status = "skipped"
        event.skipped_reason = "No notification email address is configured."
        event.save(update_fields=["status", "skipped_reason", "updated_at"])
        return event
    if quiet_hours_active(preference):
        event.skipped_reason = "Quiet hours active; email remains queued."
        event.save(update_fields=["skipped_reason", "updated_at"])
        return event
    try:
        delivered_count = send_mail(
            event.subject,
            event.body,
            settings.DEFAULT_FROM_EMAIL,
            [preference.email_address],
            fail_silently=False,
        )
    except Exception as exc:
        event.status = "failed"
        event.skipped_reason = str(exc)[:1000]
        event.save(update_fields=["status", "skipped_reason", "updated_at"])
        return event
    if delivered_count:
        event.status = "sent"
        event.sent_at = timezone.now()
        event.skipped_reason = ""
        event.save(update_fields=["status", "sent_at", "skipped_reason", "updated_at"])
    else:
        event.status = "failed"
        event.skipped_reason = "Email backend returned zero delivered messages."
        event.save(update_fields=["status", "skipped_reason", "updated_at"])
    return event


def notification_body(match) -> str:
    job = match.job
    apply_reasons = "\n".join(f"- {item}" for item in (match.reasons_to_apply or [])[:4])
    skip_reasons = "\n".join(f"- {item}" for item in (match.reasons_to_skip or [])[:4])
    return "\n".join(
        [
            f"{job.title} at {job.company.name}",
            f"Match: {match.overall_score}% | Confidence: {match.confidence_score}%",
            "",
            "Why it may fit:",
            apply_reasons or "- No strong positive evidence yet.",
            "",
            "Watch-outs:",
            skip_reasons or "- No major watch-outs detected.",
            "",
            f"Apply: {job.apply_url}",
        ]
    )


def quiet_hours_active(preference: NotificationPreference, now=None) -> bool:
    if not preference.quiet_hours_enabled:
        return False
    local_now = now or timezone.now()
    local_now = local_now.astimezone(ZoneInfo(preference.timezone))
    current = local_now.time().replace(second=0, microsecond=0)
    start = preference.quiet_hours_start
    end = preference.quiet_hours_end
    if start == end:
        return True
    if start < end:
        return start <= current < end
    return current >= start or current < end


def coerce_bool(value) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def coerce_time(value, field: str) -> time:
    if isinstance(value, time):
        return value.replace(second=0, microsecond=0)
    text = str(value or "").strip()
    try:
        parsed = datetime.strptime(text, "%H:%M").time()
    except ValueError as exc:
        raise ValueError(f"{field} must use HH:MM format.") from exc
    return parsed.replace(second=0, microsecond=0)


def validate_timezone(value: str) -> None:
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("timezone must be a valid IANA timezone name.") from exc


def validate_choice(value: str, allowed: set[str], field: str) -> None:
    if value not in allowed:
        raise ValueError(f"{field} must be one of: {', '.join(sorted(allowed))}")


def format_time(value: time) -> str:
    return value.strftime("%H:%M")


def positive_int(value, field: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a number") from exc
    if parsed < 0:
        raise ValueError(f"{field} must be zero or greater")
    return parsed
