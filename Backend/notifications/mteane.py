from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

import requests
from django.conf import settings


logger = logging.getLogger(__name__)

EVENT_TYPE_PATTERN = re.compile(r"^[a-z]+\.[a-z_]+$")
SAFE_EVENT_TYPES = {
    "job.new_role",
    "scan.failed",
    "scan.recovered",
    "application.follow_up_due",
    "agent.run_failed",
    "weekly.generated",
}
SENSITIVE_KEY_TERMS = (
    "api_key",
    "apikey",
    "authorization",
    "bearer",
    "cv",
    "notes",
    "password",
    "profile",
    "raw",
    "resume",
    "secret",
    "token",
)


@dataclass(frozen=True)
class MteanePublishResult:
    delivered: bool
    status: str
    message: str = ""


def mteane_status() -> dict:
    enabled = bool(getattr(settings, "MTEANE_ENABLED", False))
    configured = bool(getattr(settings, "MTEANE_API_URL", "") and getattr(settings, "MTEANE_API_KEY", ""))
    return {
        "enabled": enabled,
        "configured": configured,
        "status": "configured" if enabled and configured else ("disabled" if not enabled else "missing_config"),
        "api_url_configured": bool(getattr(settings, "MTEANE_API_URL", "")),
        "api_key_configured": bool(getattr(settings, "MTEANE_API_KEY", "")),
    }


def publish_mteane_event(
    event_type: str,
    payload: dict[str, Any],
    idempotency_key: str | None = None,
) -> MteanePublishResult:
    if not getattr(settings, "MTEANE_ENABLED", False):
        return MteanePublishResult(False, "disabled")

    event_type = str(event_type or "").strip()
    if event_type not in SAFE_EVENT_TYPES or not EVENT_TYPE_PATTERN.fullmatch(event_type):
        return MteanePublishResult(False, "rejected_event_type", event_type)

    api_url = str(getattr(settings, "MTEANE_API_URL", "") or "").strip().rstrip("/")
    api_key = str(getattr(settings, "MTEANE_API_KEY", "") or "").strip()
    if not api_url or not api_key:
        return MteanePublishResult(False, "missing_config")

    body: dict[str, Any] = {
        "event_type": event_type,
        "payload": redact_payload(payload),
    }
    if idempotency_key:
        body["idempotency_key"] = str(idempotency_key)[:256]

    try:
        response = requests.post(
            f"{api_url}/events",
            json=body,
            headers={"x-api-key": api_key},
            timeout=float(getattr(settings, "MTEANE_TIMEOUT_SECONDS", 3)),
        )
    except requests.RequestException as exc:
        logger.warning("MTEANE event publish failed: %s", exc)
        return MteanePublishResult(False, "request_failed", str(exc))

    if 200 <= response.status_code < 300:
        return MteanePublishResult(True, "delivered")

    logger.warning("MTEANE event publish returned HTTP %s: %s", response.status_code, response.text[:500])
    return MteanePublishResult(False, "http_error", str(response.status_code))


def redact_payload(value: Any) -> Any:
    if isinstance(value, dict):
        redacted = {}
        for key, child in value.items():
            key_text = str(key)
            key_folded = key_text.casefold()
            if any(term in key_folded for term in SENSITIVE_KEY_TERMS):
                redacted[key_text] = "[redacted]"
            else:
                redacted[key_text] = redact_payload(child)
        return redacted
    if isinstance(value, list):
        return [redact_payload(item) for item in value]
    if isinstance(value, tuple):
        return [redact_payload(item) for item in value]
    return value
