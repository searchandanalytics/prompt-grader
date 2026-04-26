"""FastAPI dependencies shared across API routers."""

from __future__ import annotations

from fastapi import Request

from app.models.schemas import ProviderConfig

# Canonical default models per provider (used when UI supplies a key but no model).
_PROVIDER_DEFAULT_MODELS: dict[str, str | None] = {
    "anthropic": "claude-sonnet-4-6",
    "openai": "gpt-4o-mini",
    "google": "gemini/gemini-1.5-flash",
    "groq": "groq/llama3-8b-8192",
    "ollama": None,  # model chosen at runtime
    "none": None,
}


async def get_provider_config(request: Request) -> ProviderConfig:
    """Resolve the judge provider config for the current request.

    Resolution priority (highest wins):
    1. ``X-Provider-Name`` + ``X-Provider-Key`` request headers (UI-session key).
    2. Server-level config cached in ``app.state.judge_config`` (env / auto-detect).

    The ``api_key`` field is intentionally excluded from serialisation
    (see ``ProviderConfig.api_key`` field) so it never leaks into logs or responses.

    Args:
        request: The current FastAPI request.

    Returns:
        A :class:`ProviderConfig` describing the resolved provider for this request.
    """
    ui_provider = request.headers.get("X-Provider-Name", "").strip().lower()
    ui_key = request.headers.get("X-Provider-Key", "").strip()

    if ui_provider and ui_key and ui_provider != "none":
        model = _PROVIDER_DEFAULT_MODELS.get(ui_provider)
        return ProviderConfig(
            provider=ui_provider,
            model=model,
            api_key=ui_key,
            key_source="ui_session",
        )

    cfg: dict[str, str | None] = getattr(request.app.state, "judge_config", {})
    provider = cfg.get("provider") or "none"
    model = cfg.get("model")

    if provider == "none":
        return ProviderConfig(provider="none", model=None, key_source="rule_based")
    if provider == "ollama":
        return ProviderConfig(provider=provider, model=model, key_source="ollama_auto")
    return ProviderConfig(provider=provider, model=model, key_source="env")
