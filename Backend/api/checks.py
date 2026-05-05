from django.conf import settings
from django.core.checks import Error, Tags, Warning, register


@register(Tags.security, deploy=True)
def deployed_auth_checks(app_configs, **kwargs):
    issues = []
    if getattr(settings, "JOB_SCOUT_REQUIRE_AUTH", False) and not getattr(settings, "JOB_SCOUT_API_TOKEN", ""):
        issues.append(
            Error(
                "JOB_SCOUT_REQUIRE_AUTH is enabled but JOB_SCOUT_API_TOKEN is empty.",
                hint="Set the same secret value in the backend JOB_SCOUT_API_TOKEN and frontend BACKEND_API_TOKEN.",
                id="job_scout.E001",
            )
        )
    if not getattr(settings, "DEBUG", False) and not getattr(settings, "JOB_SCOUT_REQUIRE_AUTH", False):
        issues.append(
            Warning(
                "JOB_SCOUT_REQUIRE_AUTH is disabled outside debug mode.",
                hint="Enable JOB_SCOUT_REQUIRE_AUTH for hosted personal deployments.",
                id="job_scout.W001",
            )
        )
    return issues
