from datetime import datetime, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.utils import timezone

from notifications.models import NotificationPreference


def get_notification_preferences() -> NotificationPreference:
    preference = NotificationPreference.objects.order_by("id").first()
    if preference:
        return preference
    return NotificationPreference.objects.create()


def update_notification_preferences(preference: NotificationPreference, updates: dict) -> NotificationPreference:
    update_fields = []
    bool_fields = ("quiet_hours_enabled", "digest_enabled")
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
        "created_at": preference.created_at.isoformat() if preference.created_at else None,
        "updated_at": preference.updated_at.isoformat() if preference.updated_at else None,
    }


def notification_preferences_status(preference: NotificationPreference | None = None) -> dict:
    preference = preference or get_notification_preferences()
    return {
        "status": "configured" if preference.quiet_hours_enabled or preference.digest_enabled else "not_configured",
        "configured": preference.quiet_hours_enabled or preference.digest_enabled,
        "quiet_hours_enabled": preference.quiet_hours_enabled,
        "quiet_hours_active": quiet_hours_active(preference),
        "digest_enabled": preference.digest_enabled,
        "digest_frequency": preference.digest_frequency,
        "digest_channel": preference.digest_channel,
        "timezone": preference.timezone,
    }


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
