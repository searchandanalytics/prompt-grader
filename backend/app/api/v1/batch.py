"""Batch grading endpoint — streams results as NDJSON."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.core.dependencies import get_provider_config
from app.core.exceptions import LLMProviderError, ProviderNotConfiguredError
from app.graders import get_grader
from app.models.schemas import BatchRequest, BatchResultItem, ProviderConfig

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/batch", tags=["batch"])


@router.post("")
async def batch_grade(
    request: BatchRequest,
    provider_config: ProviderConfig = Depends(get_provider_config),
) -> StreamingResponse:
    """Grade many prompts and stream results as newline-delimited JSON.

    Results are emitted as each item completes, so the client can start
    rendering before all items are done.

    Args:
        request: List of prompt items, rubric, and grader type.
        provider_config: Resolved judge provider (from headers or server config).

    Returns:
        StreamingResponse of NDJSON (one JSON object per line).
    """
    if not request.items:
        raise HTTPException(status_code=422, detail="No items provided.")

    grader = get_grader(
        request.grader,
        model_override=request.judge_model,
        provider_config=provider_config,
    )

    async def _stream() -> object:  # type: ignore[return]
        for i, item in enumerate(request.items):
            item_id = item.id or str(i)
            try:
                result = await grader.grade(item.prompt, request.rubric)
            except (ProviderNotConfiguredError, LLMProviderError) as exc:
                logger.warning("Batch item %s failed: %s", item_id, exc)
                row = {"id": item_id, "error": str(exc)}
                yield json.dumps(row) + "\n"
                continue

            out = BatchResultItem(id=item_id, prompt=item.prompt, result=result)
            yield out.model_dump_json() + "\n"

    return StreamingResponse(_stream(), media_type="application/x-ndjson")
