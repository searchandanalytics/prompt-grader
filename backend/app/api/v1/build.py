"""Prompt Builder endpoint — POST /api/v1/build."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from app.core.dependencies import get_provider_config
from app.core.exceptions import LLMProviderError, ProviderNotConfiguredError
from app.graders import get_grader
from app.models.schemas import (
    BuildResponse,
    GraderType,
    PromptBlueprint,
    ProviderConfig,
    Rubric,
)
from app.services.prompt_builder import build_with_llm, build_with_template

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/build", tags=["build"])

_DEFAULT_RUBRIC = Rubric()


@router.post("", response_model=BuildResponse)
async def build_prompt(
    blueprint: PromptBlueprint,
    provider_config: ProviderConfig = Depends(get_provider_config),
) -> BuildResponse:
    """Generate a production-ready prompt from a CO-STAR wizard blueprint.

    Tries LLM generation first (uses the resolved provider config, which may
    include a UI-supplied key from ``X-Provider-Key``).  Falls back silently to
    template-based assembly when:
    - no LLM provider is configured, or
    - the LLM call fails for any reason.

    After building, the prompt is auto-graded with the hybrid grader (which
    itself falls back to rule-based if no LLM is available) and the result is
    included in the response.

    Args:
        blueprint: Wizard answers collected from the frontend.
        provider_config: Resolved judge/builder provider for this request.

    Returns:
        BuildResponse with the generated prompt, explanation, source, and grade.
    """
    # ------------------------------------------------------------------
    # 1. Generate the prompt
    # ------------------------------------------------------------------
    prompt_text: str
    generated_by: str

    try:
        prompt_text = await build_with_llm(blueprint, provider_config)
        generated_by = "llm"
        explanation = (
            f"Generated using the CO-STAR framework by {provider_config.provider}."
        )
        logger.info(
            "Prompt built via LLM (provider=%s, len=%d chars)",
            provider_config.provider,
            len(prompt_text),
        )
    except (ProviderNotConfiguredError, LLMProviderError) as exc:
        logger.info("LLM build unavailable (%s) — using template fallback.", exc)
        prompt_text = build_with_template(blueprint)
        generated_by = "template"
        explanation = (
            "Assembled from your blueprint using the CO-STAR template "
            "(no LLM provider configured)."
        )

    # ------------------------------------------------------------------
    # 2. Auto-grade the generated prompt
    # ------------------------------------------------------------------
    grade_result = None
    try:
        grader = get_grader(GraderType.hybrid, provider_config=provider_config)
        grade_result = await grader.grade(prompt_text, _DEFAULT_RUBRIC)
    except Exception as exc:  # grading is best-effort — never fail the build
        logger.warning("Auto-grading failed for built prompt: %s", exc)

    return BuildResponse(
        prompt=prompt_text,
        explanation=explanation,
        generated_by=generated_by,  # type: ignore[arg-type]
        grade_result=grade_result,
    )
