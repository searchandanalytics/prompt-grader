"""Side-by-side prompt comparison endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_provider_config
from app.core.exceptions import LLMProviderError, ProviderNotConfiguredError
from app.graders import get_grader
from app.models.schemas import CompareRequest, CompareResponse, ProviderConfig

router = APIRouter(prefix="/compare", tags=["compare"])


@router.post("", response_model=CompareResponse)
async def compare_prompts(
    request: CompareRequest,
    provider_config: ProviderConfig = Depends(get_provider_config),
) -> CompareResponse:
    """Grade two prompts and return a side-by-side comparison.

    Args:
        request: Two prompt texts, rubric, and grader type.
        provider_config: Resolved judge provider (from headers or server config).

    Returns:
        CompareResponse including per-prompt results and a winner field.
    """
    grader = get_grader(
        request.grader,
        model_override=request.judge_model,
        provider_config=provider_config,
    )
    try:
        result_a, result_b = await _grade_both(grader, request)
    except ProviderNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LLMProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if result_a.score > result_b.score:
        winner = "a"
    elif result_b.score > result_a.score:
        winner = "b"
    else:
        winner = "tie"

    return CompareResponse(
        prompt_a=request.prompt_a,
        prompt_b=request.prompt_b,
        result_a=result_a,
        result_b=result_b,
        winner=winner,
    )


async def _grade_both(grader: object, request: CompareRequest) -> tuple[object, object]:  # type: ignore[type-arg]
    import asyncio  # noqa: PLC0415

    from app.graders.base import Grader  # noqa: PLC0415

    assert isinstance(grader, Grader)
    return await asyncio.gather(
        grader.grade(request.prompt_a, request.rubric),
        grader.grade(request.prompt_b, request.rubric),
    )
