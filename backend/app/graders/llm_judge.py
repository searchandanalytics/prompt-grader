"""LLM-as-judge grader via LiteLLM (multi-provider)."""

from __future__ import annotations

import json
import logging
import re

import litellm  # type: ignore[import-untyped]

from app.core.exceptions import LLMProviderError, ProviderNotConfiguredError
from app.graders.base import Grader
from app.models.schemas import GradeResult, GraderType, JudgeProvider, ProviderConfig, Rubric

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are an expert prompt engineer acting as a judge. \
Evaluate the user-submitted prompt against the provided rubric. \
Return ONLY valid JSON with the following structure — no markdown, no prose:
{
  "clarity": <float 0-100>,
  "specificity": <float 0-100>,
  "structure": <float 0-100>,
  "task_alignment": <float 0-100>,
  "safety": <float 0-100>,
  "feedback": "<one or two sentence summary>"
}
"""

# Matches the outermost {...} block spanning multiple lines (greedy).
_JSON_EXTRACT_RE = re.compile(r"\{.*\}", re.DOTALL)


def _build_user_message(prompt: str, rubric: Rubric) -> str:
    return (
        f"Rubric weights — "
        f"clarity: {rubric.clarity.weight}, "
        f"specificity: {rubric.specificity.weight}, "
        f"structure: {rubric.structure.weight}, "
        f"task_alignment: {rubric.task_alignment.weight}, "
        f"safety: {rubric.safety.weight}\n\n"
        f"Prompt to evaluate:\n{prompt}"
    )


def _parse_judge_response(raw: str) -> dict[str, object] | None:
    """Attempt to extract a valid JSON dict from raw LLM output.

    Three-layer strategy:
    1. Strip markdown fences, then ``json.loads`` on the full text.
    2. Regex-extract the outermost ``{...}`` block and ``json.loads`` on that.
    3. ``GradeResult.model_validate_json()`` on the extracted substring.
    Returns ``None`` if all layers fail — caller must degrade gracefully.

    Args:
        raw: Raw string returned by the LLM.

    Returns:
        Parsed dict if any layer succeeds, ``None`` otherwise.
    """
    stripped = raw.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("\n", 1)[-1]
        stripped = stripped.rsplit("```", 1)[0]
    stripped = stripped.strip()

    # Layer 1: direct parse
    try:
        return json.loads(stripped)  # type: ignore[return-value]
    except json.JSONDecodeError:
        pass

    # Layer 2: regex extraction of outermost {...} block
    match = _JSON_EXTRACT_RE.search(stripped)
    if match:
        candidate = match.group()
        try:
            return json.loads(candidate)  # type: ignore[return-value]
        except json.JSONDecodeError:
            pass

        # Layer 3: Pydantic model_validate_json on the extracted substring
        try:
            from app.models.schemas import GradeResult  # noqa: PLC0415

            obj = GradeResult.model_validate_json(candidate)
            return obj.model_dump()  # type: ignore[return-value]
        except Exception:  # noqa: BLE001
            pass

    return None


class LLMJudgeGrader(Grader):
    """Uses an LLM (via LiteLLM) to evaluate prompts against a rubric."""

    def __init__(
        self,
        model_override: str | None = None,
        provider_config: ProviderConfig | None = None,
    ) -> None:
        self._model_override = model_override
        self._provider_config = provider_config

    async def grade(self, prompt: str, rubric: Rubric) -> GradeResult:
        """Grade *prompt* by calling the configured LLM judge.

        If the LLM returns a response that cannot be parsed after all recovery
        attempts, the grader silently falls back to rule-based scoring and sets
        ``metadata.parse_fallback = True``.  The user never sees a raw exception.

        Args:
            prompt: The prompt text to evaluate.
            rubric: Criteria with weights forwarded to the judge.

        Returns:
            GradeResult populated from the LLM's JSON response, or from
            rule-based scoring if parsing fails.

        Raises:
            ProviderNotConfiguredError: If no judge config is available.
            LLMProviderError: If the LLM call itself fails (network, auth, etc.).
        """
        provider, model, api_key = self._resolve_config()

        if not provider or provider == JudgeProvider.none:
            raise ProviderNotConfiguredError(
                "No LLM provider configured. Use rule_based grader or configure a provider."
            )

        try:
            extra: dict[str, object] = {}
            if api_key:
                extra["api_key"] = api_key

            response = await litellm.acompletion(
                model=model or provider,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": _build_user_message(prompt, rubric)},
                ],
                temperature=0.0,
                max_tokens=512,
                **extra,
            )
        except Exception as exc:
            # Redact any key material from the error message before logging.
            safe_msg = _redact(str(exc), api_key)
            logger.error("LLM judge call failed: %s", safe_msg)
            raise LLMProviderError(safe_msg) from exc

        raw = response.choices[0].message.content or ""

        if not raw.strip():
            logger.error(
                "LLM returned empty response (model=%s). It may be an embedding-only model.", model
            )
            raise LLMProviderError(
                f"The model '{model}' returned an empty response. "
                "Embedding models (e.g. nomic-embed-text) cannot grade prompts — "
                "please select a chat model such as phi3, llama3, or mistral."
            )

        data = _parse_judge_response(raw)
        if data is None:
            # All parse layers failed — degrade to rule-based silently.
            logger.warning(
                "LLM judge response could not be parsed; falling back to rule-based. "
                "Raw output length: %d chars.",
                len(raw),
            )
            return await self._rule_based_fallback(prompt, rubric)

        breakdown = {
            "clarity": float(data.get("clarity", 0)),  # type: ignore[arg-type]
            "specificity": float(data.get("specificity", 0)),  # type: ignore[arg-type]
            "structure": float(data.get("structure", 0)),  # type: ignore[arg-type]
            "task_alignment": float(data.get("task_alignment", 0)),  # type: ignore[arg-type]
            "safety": float(data.get("safety", 0)),  # type: ignore[arg-type]
        }

        weights = {
            "clarity": rubric.clarity.weight,
            "specificity": rubric.specificity.weight,
            "structure": rubric.structure.weight,
            "task_alignment": rubric.task_alignment.weight,
            "safety": rubric.safety.weight,
        }
        total_weight = sum(weights.values()) or 1.0
        score = sum(breakdown[k] * weights[k] for k in breakdown) / total_weight

        provider_enum = (
            JudgeProvider(provider)
            if provider in JudgeProvider._value2member_map_
            else JudgeProvider.none
        )

        return GradeResult(
            score=round(score, 2),
            breakdown={k: round(v, 2) for k, v in breakdown.items()},
            feedback=str(data.get("feedback", "")),
            grader=GraderType.llm_judge,
            provider=provider_enum,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_config(self) -> tuple[str | None, str | None, str | None]:
        """Return (provider, model, api_key) for this grader instance.

        Priority:
        1. Injected ``ProviderConfig`` (from request headers).
        2. ``model_override`` constructor arg (legacy Ollama model-swap path).
        3. ``app.state.judge_config`` (startup auto-detection).
        """
        if self._provider_config is not None:
            cfg = self._provider_config
            model = self._model_override or cfg.model
            return cfg.provider, model, cfg.api_key

        # Import here to avoid circular dependency at module load time.
        from app.main import app  # noqa: PLC0415

        judge_config: dict[str, str | None] = getattr(app.state, "judge_config", {})
        provider = judge_config.get("provider")
        model = self._model_override or judge_config.get("model")
        return provider, model, None

    async def _rule_based_fallback(self, prompt: str, rubric: Rubric) -> GradeResult:
        """Grade with rule-based grader and mark result as a parse fallback."""
        from app.graders.rule_based import RuleBasedGrader  # noqa: PLC0415

        rb_result = await RuleBasedGrader().grade(prompt, rubric)
        return GradeResult(
            score=rb_result.score,
            breakdown=rb_result.breakdown,
            feedback="Judge response could not be parsed. Showing rule-based score only.",
            grader=GraderType.llm_judge,
            provider=JudgeProvider.none,
            metadata={"parse_fallback": True},
        )


def _redact(text: str, secret: str | None) -> str:
    """Remove *secret* from *text* so it never reaches log sinks."""
    if not secret:
        return text
    return text.replace(secret, "***REDACTED***")
