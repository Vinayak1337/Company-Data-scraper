from __future__ import annotations

from django.conf import settings
from django.http import JsonResponse


class ApiTokenMiddleware:
    """Optional single-user API guard for deployed personal instances."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if should_require_api_token(request.path):
            configured_token = str(getattr(settings, "JOB_SCOUT_API_TOKEN", "") or "").strip()
            if not configured_token:
                return JsonResponse(
                    {"error": "API authentication is required but JOB_SCOUT_API_TOKEN is not configured."},
                    status=503,
                )

            supplied_token = extract_bearer_token(request.META.get("HTTP_AUTHORIZATION", ""))
            if supplied_token != configured_token:
                return JsonResponse({"error": "Authentication required."}, status=401)

        return self.get_response(request)


def should_require_api_token(path: str) -> bool:
    if not getattr(settings, "JOB_SCOUT_REQUIRE_AUTH", False):
        return False
    return path.startswith("/api/") and path != "/api/health"


def extract_bearer_token(value: str) -> str:
    scheme, _, token = value.partition(" ")
    if scheme.lower() != "bearer":
        return ""
    return token.strip()
