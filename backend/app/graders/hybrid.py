"""Hybrid grader — runs rule-based first, then optionally blends with LLM judge."""

from __future__ import annotations

import logging

from app.core.config import settings
from app.core.exceptions import ProviderNotConfiguredError
from app.graders.base import Grader
from app.graders.llm_judge import LLMJudgeGrader
from app.graders.rule_based import RuleBasedGrader
from app.models.schemas import GradeResult, GraderType, ProviderConfig, Rubric

logger = logging.getLogger(__name__)


class HybridGrader(Grader):
    """Blends rule-based (cheap) and LLM-judge (rich) scores.

    Default weights: 30 % rules + 70 % LLM, configurable via
    ``RULES_WEIGHT`` / ``LLM_WEIGHT`` env vars.

    If no LLM provider is configured the grader silently falls back to
    rule-based-only and sets ``metadata.fallback = True``.
    """

    def __init__(
        self,
        model_override: str | None = None,
        provider_config: ProviderConfig | None = None,
    ) -> None:
        self._rule_grader = RuleBasedGrader()
        self._llm_grader = LLMJudgeGrader(
            model_override=model_override,
            provider_config=provider_config,
        )

    async def grade(self, prompt: str, rubric: Rubric) -> GradeResult:
        """Grade using a weighted blend of rules and LLM judge.

        Args:
            prompt: The prompt text to evaluate.
            rubric: Criteria weights forwarded to both sub-graders.

        Returns:
            GradeResult whose score is a weighted combination.
        """
        rule_result = await self._rule_grader.grade(prompt, rubric)

        try:
            llm_result = await self._llm_grader.grade(prompt, rubric)
        except ProviderNotConfiguredError:
            logger.info("No LLM provider configured — hybrid falling back to rule-based.")
            return GradeResult(
                score=rule_result.score,
                breakdown=rule_result.breakdown,
                feedback=rule_result.feedback,
                grader=GraderType.hybrid,
                provider=rule_result.provider,
                metadata={"fallback": True, "reason": "no_llm_provider"},
            )

        rw = settings.rules_weight
        lw = settings.llm_weight
        total = rw + lw or 1.0

        blended_breakdown = {
            k: round((rule_result.breakdown.get(k, 0) * rw + llm_result.breakdown.get(k, 0) * lw) / total, 2)
            for k in rule_result.breakdown
        }
        blended_score = round((rule_result.score * rw + llm_result.score * lw) / total, 2)
        feedback = llm_result.feedback or rule_result.feedback

        return GradeResult(
            score=blended_score,
            breakdown=blended_breakdown,
            feedback=feedback,
            grader=GraderType.hybrid,
            provider=llm_result.provider,
            metadata={
                "rules_score": rule_result.score,
                "llm_score": llm_result.score,
                "rules_weight": rw,
                "llm_weight": lw,
            },
        )
