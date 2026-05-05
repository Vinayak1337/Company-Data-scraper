from __future__ import annotations

import os
import uuid
from collections.abc import Callable
from typing import Any

from django.conf import settings


SENSITIVE_TRACE_KEYS = {
    "cv_markdown",
    "profile_markdown",
    "resume_text",
    "cv_text",
    "raw_resume",
    "raw_cv",
}


def langsmith_enabled() -> bool:
    tracing = bool(getattr(settings, "LANGSMITH_TRACING", False))
    return tracing and bool(os.environ.get("LANGSMITH_API_KEY"))


def langsmith_status() -> dict:
    tracing = bool(getattr(settings, "LANGSMITH_TRACING", False))
    api_key_configured = bool(os.environ.get("LANGSMITH_API_KEY"))
    return {
        "name": "LangSmith observability",
        "status": "configured" if tracing and api_key_configured else "not_configured",
        "configured": tracing and api_key_configured,
        "tracing_enabled": tracing,
        "api_key_configured": api_key_configured,
        "project": getattr(settings, "LANGSMITH_PROJECT", "") or "default",
        "message": (
            "Optional AI tracing is active."
            if tracing and api_key_configured
            else "Set LANGSMITH_TRACING=true and LANGSMITH_API_KEY to trace AI runs."
        ),
    }


def execute_with_optional_langsmith(run, payload: dict, execute: Callable[[], Any]) -> tuple[Any, dict | None]:
    if not langsmith_enabled():
        return execute(), None

    trace_id = uuid.uuid4()
    metadata = {
        "trace_id": str(trace_id),
        "project": getattr(settings, "LANGSMITH_PROJECT", "") or "default",
        "provider": run.provider,
        "model_name": run.model_name,
        "agent_type": run.agent_type,
        "tool_policy": run.tool_policy,
        "prompt_version": run.prompt_version,
    }
    holder: dict[str, Any] = {}

    try:
        from langsmith import traceable
    except Exception as exc:
        result = execute()
        return result, metadata | {"status": "unavailable", "error_type": exc.__class__.__name__}

    def traced_execution(trace_payload: dict) -> dict:
        holder["execute_started"] = True
        result = execute()
        holder["result"] = result
        return {
            "status": result.status,
            "output": result.output,
            "error": result.error,
            "token_count": result.token_count,
            "cost_estimate": float(result.cost_estimate or 0),
        }

    try:
        traced = traceable(
            name=f"job-scout.{run.agent_type}",
            run_type="chain",
            metadata=metadata,
        )(traced_execution)
        traced(redact_for_trace(payload), langsmith_extra={"run_id": trace_id})
        return holder["result"], metadata | {"status": "traced"}
    except Exception as exc:
        if holder.get("result") is not None:
            return holder["result"], metadata | {"status": "trace_failed_after_execute", "error_type": exc.__class__.__name__}
        if holder.get("execute_started"):
            raise
        result = execute()
        return result, metadata | {"status": "trace_failed_before_execute", "error_type": exc.__class__.__name__}


def redact_for_trace(value: Any) -> Any:
    if isinstance(value, dict):
        redacted = {}
        for key, item in value.items():
            if str(key) in SENSITIVE_TRACE_KEYS and item:
                redacted[key] = f"[redacted {key}, {len(str(item))} chars]"
            else:
                redacted[key] = redact_for_trace(item)
        return redacted
    if isinstance(value, list):
        return [redact_for_trace(item) for item in value]
    return value
