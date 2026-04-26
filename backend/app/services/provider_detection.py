"""Auto-detect the best available LLM judge provider at startup.

Detection order (per CLAUDE.md):
  1. JUDGE_PROVIDER env var override
  2. First paid API key found (Anthropic > OpenAI > Google > Groq)
  3. Ping Ollama with 1-second timeout
  4. Fallback to rule-based only
"""

from __future__ import annotations

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_PAID_KEY_MAP = [
    ("anthropic", settings.anthropic_api_key, "claude-sonnet-4-6"),
    ("openai", settings.openai_api_key, "gpt-4o-mini"),
    ("google", settings.google_api_key, "gemini/gemini-1.5-flash"),
    ("groq", settings.groq_api_key, "groq/llama3-8b-8192"),
]

_OLLAMA_DEFAULT_MODEL = "llama3.1:8b"
_OLLAMA_FALLBACK_MODEL = None  # picked dynamically from tag list

# Substrings that identify embedding-only models — these cannot generate chat completions.
_EMBEDDING_MODEL_PATTERNS = ("embed", "minilm", "bge-", "e5-", "gte-")


def _is_embedding_model(name: str) -> bool:
    """Return True if the model name looks like an embedding-only model."""
    lower = name.lower()
    return any(pat in lower for pat in _EMBEDDING_MODEL_PATTERNS)


async def list_ollama_models() -> list[str]:
    """Return chat-capable model names currently registered in Ollama.

    Embedding-only models (e.g. nomic-embed-text) are excluded because they
    cannot generate text completions and will cause grading to fail.
    """
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            if resp.status_code == 200:
                tags = resp.json().get("models", [])
                return [
                    str(t.get("name", ""))
                    for t in tags
                    if t.get("name") and not _is_embedding_model(str(t.get("name", "")))
                ]
    except Exception:
        pass
    return []


async def health_check_provider(provider: str, timeout: float = 1.5) -> bool:
    """Quickly verify the provider is still reachable.

    For Ollama: pings ``/api/tags`` with a short timeout.
    For paid providers: checks that the env API key is still present
    (no LLM call — would cost money and slow down every status poll).
    Rule-based always returns True.

    Args:
        provider: The provider string (e.g. ``"ollama"``, ``"anthropic"``).
        timeout: Network timeout in seconds for Ollama ping.

    Returns:
        ``True`` if the provider is considered healthy, ``False`` otherwise.
    """
    if provider == "ollama":
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                r = await client.get(f"{settings.ollama_base_url}/api/tags")
                return r.status_code == 200
        except Exception:
            return False

    if provider in ("anthropic", "openai", "google", "groq"):
        # A real LLM call would cost money on every status poll, so we just
        # verify the key is still configured.  Keys don't disappear at runtime.
        key_map = {
            "anthropic": settings.anthropic_api_key,
            "openai": settings.openai_api_key,
            "google": settings.google_api_key,
            "groq": settings.groq_api_key,
        }
        return bool(key_map.get(provider))

    # "none" / rule_based — always healthy (no external dependency)
    return True


async def detect_provider() -> dict[str, str | None]:
    """Run provider detection and return a config dict.

    Returns:
        Dict with keys ``provider`` (str) and ``model`` (str | None).
    """
    # 1. Explicit env override
    if settings.judge_provider:
        logger.info("Judge provider explicitly set: %s", settings.judge_provider)
        return {
            "provider": settings.judge_provider,
            "model": settings.judge_model,
        }

    # 2. First paid API key present
    for provider, key, default_model in _PAID_KEY_MAP:
        if key:
            model = settings.judge_model or default_model
            logger.info("Detected paid API key for %s — using model %s", provider, model)
            return {"provider": provider, "model": model}

    # 3. Ping Ollama
    try:
        async with httpx.AsyncClient(timeout=1.0) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            if resp.status_code == 200:
                tags = resp.json().get("models", [])
                model = await _pick_ollama_model(tags, client)
                if model:
                    logger.info("Ollama detected — using model %s", model)
                    return {"provider": "ollama", "model": f"ollama/{model}"}
                logger.warning("Ollama is running but no usable models found.")
    except Exception:
        pass  # Ollama not reachable

    # 4. Fallback
    logger.info("No LLM provider found — running in rule-based only mode.")
    return {"provider": "none", "model": None}


async def _pick_ollama_model(
    tags: list[dict[str, object]], client: httpx.AsyncClient
) -> str | None:
    """Pick a sensible, verified default from the list of available Ollama models.

    Returns the first model name that Ollama confirms is usable via /api/show,
    or None if no model can be verified.
    """
    names = [
        str(t.get("name", ""))
        for t in tags
        if t.get("name") and not _is_embedding_model(str(t.get("name", "")))
    ]

    # Build a priority-ordered candidate list
    preferred = [n for n in names if "llama3.1:8b" in n or n == "llama3.1:8b"]
    mistral = [n for n in names if "mistral" in n]
    rest = [n for n in names if n not in preferred and n not in mistral]
    candidates = preferred + mistral + rest

    for name in candidates:
        if await _ollama_model_available(name, client):
            return name

    return None


async def _ollama_model_available(name: str, client: httpx.AsyncClient) -> bool:
    """Return True if Ollama confirms the model is present and usable."""
    try:
        resp = await client.post(
            f"{settings.ollama_base_url}/api/show",
            json={"name": name},
            timeout=2.0,
        )
        return resp.status_code == 200
    except Exception:
        return False
