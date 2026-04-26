"""Grader registry — maps GraderType enum values to implementation classes."""

from __future__ import annotations

from app.graders.base import Grader
from app.graders.hybrid import HybridGrader
from app.graders.llm_judge import LLMJudgeGrader
from app.graders.rule_based import RuleBasedGrader
from app.models.schemas import GraderType, ProviderConfig

_REGISTRY: dict[GraderType, type[Grader]] = {
    GraderType.rule_based: RuleBasedGrader,
    GraderType.llm_judge: LLMJudgeGrader,
    GraderType.hybrid: HybridGrader,
}


def get_grader(
    grader_type: GraderType,
    model_override: str | None = None,
    provider_config: ProviderConfig | None = None,
) -> Grader:
    """Return an instantiated grader for the given type.

    Args:
        grader_type: Which grader implementation to use.
        model_override: Optional model name to use instead of the configured default.
            Only applied to LLM-backed graders; ignored by rule_based.
        provider_config: Per-request provider config (e.g. from UI-supplied headers).
            Takes precedence over server-level config for LLM-backed graders.

    Returns:
        An instance of the corresponding Grader subclass.

    Raises:
        KeyError: If grader_type is not registered.
    """
    cls = _REGISTRY[grader_type]
    if grader_type in (GraderType.llm_judge, GraderType.hybrid):
        return cls(  # type: ignore[call-arg]
            model_override=model_override,
            provider_config=provider_config,
        )
    return cls()


__all__ = ["Grader", "RuleBasedGrader", "LLMJudgeGrader", "HybridGrader", "get_grader"]
