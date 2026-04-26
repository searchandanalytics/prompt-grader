"""Shared pytest fixtures."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import Rubric


@pytest.fixture()
def client() -> TestClient:
    """Synchronous test client with rule-based judge config pre-set."""
    app.state.judge_config = {"provider": "none", "model": None}
    return TestClient(app)


@pytest.fixture()
def default_rubric() -> Rubric:
    """Return the default equal-weight rubric."""
    return Rubric()
