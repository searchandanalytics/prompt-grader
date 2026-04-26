"""Single-prompt grading endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_provider_config
from app.core.exceptions import LLMProviderError, ProviderNotConfiguredError
from app.graders import get_grader
from app.models.schemas import GradeRequest, GradeResponse, ProviderConfig

router = APIRouter(prefix="/grade", tags=["grade"])


@router.post("", response_model=GradeResponse)
async def grade_prompt(
    request: GradeRequest,
    provider_config: ProviderConfig = Depends(get_provider_config),
) -> GradeResponse:
    """Grade a single prompt against a rubric.

    Args:
        request: Prompt text, rubric, and grader type.
        provider_config: Resolved judge provider (from headers or server config).

    Returns:
        GradeResponse with score, breakdown, and feedback.
    """
    grader = get_grader(
        request.grader,
        model_override=request.judge_model,
        provider_config=provider_config,
    )
    try:
        result = await grader.grade(request.prompt, request.rubric)
    except ProviderNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LLMProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return GradeResponse(prompt=request.prompt, result=result)
