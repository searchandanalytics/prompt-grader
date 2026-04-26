"""Status endpoints — exposes active judge config to the frontend."""

from __future__ import annotations

import logging
import time

import litellm  # type: ignore[import-untyped]
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.core.dependencies import get_provider_config
from app.models.schemas import (
    JudgeProvider,
    ProviderConfig,
    StatusResponse,
    TestConnectionResponse,
)
from app.services.provider_detection import (
    detect_provider,
    health_check_provider,
    list_ollama_models,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/status", tags=["status"])


def _build_status_response(
    cfg: dict[str, str | None],
    unhealthy_reason: str | None = None,
) -> StatusResponse:
    provider_str = cfg.get("provider", "none")
    try:
        provider = JudgeProvider(provider_str)
    except ValueError:
        provider = JudgeProvider.none

    mode = "rule_based" if provider == JudgeProvider.none else "hybrid"

    if provider == JudgeProvider.none:
        key_source: str = "rule_based"
    elif provider == JudgeProvider.ollama:
        key_source = "ollama_auto"
    else:
        key_source = "env"

    return StatusResponse(
        judge_provider=provider,
        judge_model=cfg.get("model"),
        mode=mode,
        key_source=key_source,  # type: ignore[arg-type]
        unhealthy_reason=unhealthy_reason,
    )


def _fallback_reason(old_provider: str, new_provider: str) -> str:
    """Return a human-readable explanation of an automatic provider fallback."""
    old_label = old_provider.capitalize() if old_provider != "none" else "The configured provider"
    new_label = "rule-based mode" if new_provider == "none" else new_provider.capitalize()
    return f"{old_label} is not reachable. Switched to {new_label}."


@router.get("", response_model=StatusResponse)
async def get_status(request: Request) -> StatusResponse:
    """Return a live status for the active judge provider.

    On every call this performs a lightweight health check on the currently
    cached provider (1.5 s timeout).  If the provider is no longer reachable
    the server re-runs the full detection chain, updates ``app.state``, and
    returns the new provider together with an ``unhealthy_reason`` field so
    the frontend can notify the user exactly once.

    Rule-based mode always passes the health check, so once the server falls
    back it stays there until an explicit ``POST /status/refresh``.
    """
    cfg: dict[str, str | None] = getattr(request.app.state, "judge_config", {})
    provider = cfg.get("provider", "none")

    is_healthy = await health_check_provider(provider)
    if is_healthy:
        return _build_status_response(cfg)

    # Provider is down — re-detect and update the cache so grading requests
    # also benefit from the new config immediately.
    logger.warning("Provider %s failed health check — re-detecting.", provider)
    new_cfg = await detect_provider()
    request.app.state.judge_config = new_cfg
    new_provider = new_cfg.get("provider", "none")
    reason = _fallback_reason(provider, new_provider)
    logger.info("Fell back from %s to %s: %s", provider, new_provider, reason)
    return _build_status_response(new_cfg, unhealthy_reason=reason)


@router.get("/ollama-models")
async def get_ollama_models() -> dict[str, list[str]]:
    """Return all model names currently available in Ollama."""
    return {"models": await list_ollama_models()}


class _SetModelBody(BaseModel):
    model: str


@router.post("/set-model", response_model=StatusResponse)
async def set_model(request: Request, body: _SetModelBody) -> StatusResponse:
    """Persist a user-selected Ollama model to the active judge config."""
    cfg = getattr(request.app.state, "judge_config", {})
    if cfg.get("provider") != "ollama":
        raise HTTPException(
            status_code=400,
            detail="set-model is only supported when provider is ollama",
        )
    model = body.model if body.model.startswith("ollama/") else f"ollama/{body.model}"
    cfg["model"] = model
    request.app.state.judge_config = cfg
    return _build_status_response(cfg)


@router.post("/refresh", response_model=StatusResponse)
async def refresh_status(request: Request) -> StatusResponse:
    """Re-run provider detection (useful after installing Ollama without restart)."""
    cfg = await detect_provider()
    request.app.state.judge_config = cfg
    return _build_status_response(cfg)


@router.post("/test", response_model=TestConnectionResponse)
async def test_connection(
    provider_config: ProviderConfig = Depends(get_provider_config),
) -> TestConnectionResponse:
    """Test connectivity to the resolved LLM provider with a 1-token completion.

    Reads ``X-Provider-Name`` / ``X-Provider-Key`` headers if present so the
    frontend can validate a UI-supplied key before saving it.

    Args:
        provider_config: Resolved provider from headers or server config.

    Returns:
        TestConnectionResponse with ``ok=True`` and latency, or ``ok=False``
        and a friendly ``error`` message.
    """
    provider = provider_config.provider
    model = provider_config.model
    api_key = provider_config.api_key

    if not provider or provider == "none":
        return TestConnectionResponse(
            ok=False,
            provider="none",
            error="No provider configured. Add an API key or install Ollama.",
        )

    extra: dict[str, object] = {}
    if api_key:
        extra["api_key"] = api_key

    start = time.perf_counter()
    try:
        await litellm.acompletion(
            model=model or provider,
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=1,
            **extra,
        )
        latency_ms = round((time.perf_counter() - start) * 1000, 1)
        return TestConnectionResponse(
            ok=True,
            provider=provider,
            model=model,
            latency_ms=latency_ms,
        )
    except Exception as exc:
        # Redact the key from any error string before returning.
        safe_error = str(exc)
        if api_key:
            safe_error = safe_error.replace(api_key, "***REDACTED***")
        logger.warning("Provider test failed for %s: %s", provider, safe_error)
        return TestConnectionResponse(
            ok=False,
            provider=provider,
            model=model,
            error=_friendly_error(safe_error),
        )


def _friendly_error(raw: str) -> str:
    """Convert a raw LiteLLM error string into a user-readable message."""
    low = raw.lower()
    if "auth" in low or "api key" in low or "unauthorized" in low or "401" in low:
        return "Invalid API key. Please check your key and try again."
    if "model" in low and ("not found" in low or "does not exist" in low):
        return f"Model not found: {raw[:120]}"
    if "connect" in low or "timeout" in low or "refused" in low:
        return "Could not reach the provider. Check your network or Ollama is running."
    return raw[:200]
