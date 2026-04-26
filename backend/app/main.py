"""FastAPI application entrypoint for PromptGrade."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import batch, build, compare, grade, status
from app.core.config import settings
from app.core.logging import configure_logging
from app.services.provider_detection import detect_provider

configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    """Run startup / shutdown logic."""
    # Detect LLM provider once; cache in app.state
    application.state.judge_config = await detect_provider()
    cfg = application.state.judge_config
    logger.info(
        "PromptGrade started — provider=%s model=%s",
        cfg.get("provider", "none"),
        cfg.get("model", "n/a"),
    )
    yield
    logger.info("PromptGrade shutting down.")


app = FastAPI(
    title="PromptGrade",
    description="Open-source prompt grading platform.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://localhost:\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
_PREFIX = "/api/v1"
app.include_router(grade.router, prefix=_PREFIX)
app.include_router(compare.router, prefix=_PREFIX)
app.include_router(batch.router, prefix=_PREFIX)
app.include_router(status.router, prefix=_PREFIX)
app.include_router(build.router, prefix=_PREFIX)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    """Simple liveness probe."""
    return {"status": "ok"}
