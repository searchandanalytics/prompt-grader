"""Tests for Feature 1: BYOK Provider Selection.

Covers:
- X-Provider-Name / X-Provider-Key headers override server config
- Fallback to server env config when no headers present
- Fallback to rule-based when no provider configured
- Multi-layer JSON parsing: clean JSON, markdown-fenced, regex-extractable, unparseable
- /status/test endpoint success and failure paths
- API keys are never echoed in responses or errors

All LLM calls are mocked with pytest-mock to avoid spending API credits.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import GraderType, JudgeProvider, Rubric


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def client_no_provider() -> TestClient:
    """Client with rule-based-only server config (no LLM at server level)."""
    app.state.judge_config = {"provider": "none", "model": None}
    return TestClient(app)


@pytest.fixture()
def client_anthropic_env() -> TestClient:
    """Client with Anthropic configured at server level (env key)."""
    app.state.judge_config = {"provider": "anthropic", "model": "claude-sonnet-4-6"}
    return TestClient(app)


@pytest.fixture()
def rubric() -> Rubric:
    return Rubric()


def _mock_llm_response(content: str) -> MagicMock:
    """Build a fake litellm response with the given message content."""
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


_VALID_JSON = (
    '{"clarity": 85, "specificity": 78, "structure": 82, '
    '"task_alignment": 90, "safety": 100, "feedback": "Looks good."}'
)

_FENCED_JSON = f"```json\n{_VALID_JSON}\n```"

_PROSE_THEN_JSON = f"Here is my evaluation:\n{_VALID_JSON}\nDone."

_UNPARSEABLE = "Sorry, I cannot evaluate this prompt."


# ---------------------------------------------------------------------------
# get_provider_config dependency
# ---------------------------------------------------------------------------


def test_no_headers_uses_server_config(client_anthropic_env: TestClient) -> None:
    """Without headers the dependency falls back to app.state.judge_config."""
    resp = client_anthropic_env.get("/api/v1/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["judge_provider"] == "anthropic"
    assert data["key_source"] == "env"


def test_no_provider_gives_rule_based_key_source(client_no_provider: TestClient) -> None:
    """Rule-based-only config returns key_source='rule_based'."""
    resp = client_no_provider.get("/api/v1/status")
    assert resp.status_code == 200
    assert resp.json()["key_source"] == "rule_based"


# ---------------------------------------------------------------------------
# Header-supplied key overrides server config
# ---------------------------------------------------------------------------


def test_ui_key_header_used_for_grading(
    client_no_provider: TestClient,
    mocker: Any,
) -> None:
    """X-Provider-Key header is forwarded to LiteLLM; server config is ignored."""
    mock_completion = AsyncMock(return_value=_mock_llm_response(_VALID_JSON))
    mocker.patch("litellm.acompletion", mock_completion)

    resp = client_no_provider.post(
        "/api/v1/grade",
        json={"prompt": "Write a Python function.", "grader": "llm_judge"},
        headers={"X-Provider-Name": "anthropic", "X-Provider-Key": "sk-test-key"},
    )

    assert resp.status_code == 200
    result = resp.json()["result"]
    assert result["score"] > 0

    # Verify acompletion was called with the UI-supplied key.
    call_kwargs = mock_completion.call_args.kwargs
    assert call_kwargs.get("api_key") == "sk-test-key"


def test_ui_key_not_in_response(
    client_no_provider: TestClient,
    mocker: Any,
) -> None:
    """The API key must never appear anywhere in the response body."""
    mocker.patch("litellm.acompletion", AsyncMock(return_value=_mock_llm_response(_VALID_JSON)))

    secret = "sk-super-secret-key-12345"
    resp = client_no_provider.post(
        "/api/v1/grade",
        json={"prompt": "Explain recursion.", "grader": "llm_judge"},
        headers={"X-Provider-Name": "openai", "X-Provider-Key": secret},
    )

    assert secret not in resp.text


def test_ui_key_not_in_error_response(
    client_no_provider: TestClient,
    mocker: Any,
) -> None:
    """If the LLM call fails, the API key must not leak into the error message."""
    secret = "sk-leaked-key-99999"
    mocker.patch(
        "litellm.acompletion",
        AsyncMock(side_effect=Exception(f"AuthenticationError: bad key {secret}")),
    )

    resp = client_no_provider.post(
        "/api/v1/grade",
        json={"prompt": "Hello.", "grader": "llm_judge"},
        headers={"X-Provider-Name": "anthropic", "X-Provider-Key": secret},
    )

    assert resp.status_code == 502
    assert secret not in resp.text


# ---------------------------------------------------------------------------
# JSON parsing robustness
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "llm_output",
    [
        _VALID_JSON,
        _FENCED_JSON,
        _PROSE_THEN_JSON,
    ],
    ids=["clean_json", "markdown_fenced", "prose_then_json"],
)
def test_parseable_llm_responses_succeed(
    client_no_provider: TestClient,
    mocker: Any,
    llm_output: str,
) -> None:
    """All parseable formats should yield a valid score without errors."""
    mocker.patch("litellm.acompletion", AsyncMock(return_value=_mock_llm_response(llm_output)))

    resp = client_no_provider.post(
        "/api/v1/grade",
        json={"prompt": "Explain sorting algorithms.", "grader": "llm_judge"},
        headers={"X-Provider-Name": "anthropic", "X-Provider-Key": "sk-test"},
    )

    assert resp.status_code == 200
    result = resp.json()["result"]
    assert 0.0 <= result["score"] <= 100.0


def test_unparseable_llm_response_falls_back_to_rule_based(
    client_no_provider: TestClient,
    mocker: Any,
) -> None:
    """Completely unparseable LLM output should fall back to rule-based, not 500."""
    mocker.patch(
        "litellm.acompletion", AsyncMock(return_value=_mock_llm_response(_UNPARSEABLE))
    )

    resp = client_no_provider.post(
        "/api/v1/grade",
        json={"prompt": "Write a haiku.", "grader": "llm_judge"},
        headers={"X-Provider-Name": "anthropic", "X-Provider-Key": "sk-test"},
    )

    assert resp.status_code == 200
    result = resp.json()["result"]
    # Rule-based fallback produces a valid score.
    assert 0.0 <= result["score"] <= 100.0
    assert "could not be parsed" in result["feedback"].lower()
    assert result["metadata"].get("parse_fallback") is True


def test_unparseable_response_never_raises_500(
    client_no_provider: TestClient,
    mocker: Any,
) -> None:
    """JSON parse failure must never produce a 5xx response."""
    mocker.patch(
        "litellm.acompletion",
        AsyncMock(return_value=_mock_llm_response("not json at all!!!")),
    )

    resp = client_no_provider.post(
        "/api/v1/grade",
        json={"prompt": "Hello world.", "grader": "llm_judge"},
        headers={"X-Provider-Name": "anthropic", "X-Provider-Key": "sk-test"},
    )

    assert resp.status_code < 500


# ---------------------------------------------------------------------------
# Rule-based fallback when no provider
# ---------------------------------------------------------------------------


def test_grade_rule_based_needs_no_provider(client_no_provider: TestClient) -> None:
    """rule_based grader works without any LLM provider configured."""
    resp = client_no_provider.post(
        "/api/v1/grade",
        json={"prompt": "Explain Newton's laws of motion.", "grader": "rule_based"},
    )
    assert resp.status_code == 200
    assert resp.json()["result"]["score"] > 0


def test_llm_judge_without_provider_returns_503(client_no_provider: TestClient) -> None:
    """Requesting llm_judge with no provider and no UI key returns 503."""
    resp = client_no_provider.post(
        "/api/v1/grade",
        json={"prompt": "Hello.", "grader": "llm_judge"},
    )
    assert resp.status_code == 503


def test_hybrid_without_provider_falls_back_silently(client_no_provider: TestClient) -> None:
    """hybrid grader silently falls back to rule-based when no provider is available."""
    resp = client_no_provider.post(
        "/api/v1/grade",
        json={"prompt": "Explain recursion clearly with an example.", "grader": "hybrid"},
    )
    assert resp.status_code == 200
    result = resp.json()["result"]
    assert result["metadata"].get("fallback") is True


# ---------------------------------------------------------------------------
# /status/test endpoint
# ---------------------------------------------------------------------------


def test_status_test_success(client_no_provider: TestClient, mocker: Any) -> None:
    """Successful provider test returns ok=True with latency_ms."""
    mock_completion = AsyncMock(return_value=_mock_llm_response("hi"))
    mocker.patch("litellm.acompletion", mock_completion)

    resp = client_no_provider.post(
        "/api/v1/status/test",
        headers={"X-Provider-Name": "anthropic", "X-Provider-Key": "sk-valid-key"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["provider"] == "anthropic"
    assert data["latency_ms"] is not None
    assert data["latency_ms"] >= 0


def test_status_test_failure_returns_friendly_error(
    client_no_provider: TestClient,
    mocker: Any,
) -> None:
    """Failed provider test returns ok=False with a friendly error, not a 5xx."""
    mocker.patch(
        "litellm.acompletion",
        AsyncMock(side_effect=Exception("AuthenticationError: Invalid API key 401")),
    )

    resp = client_no_provider.post(
        "/api/v1/status/test",
        headers={"X-Provider-Name": "anthropic", "X-Provider-Key": "sk-bad"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert "invalid api key" in data["error"].lower()


def test_status_test_no_provider_returns_error(client_no_provider: TestClient) -> None:
    """Calling /status/test with no provider returns ok=False (no 5xx)."""
    resp = client_no_provider.post("/api/v1/status/test")
    assert resp.status_code == 200
    assert resp.json()["ok"] is False


def test_status_test_key_not_in_error(
    client_no_provider: TestClient,
    mocker: Any,
) -> None:
    """API key must not appear in the test error response."""
    secret = "sk-should-not-appear-9876"
    mocker.patch(
        "litellm.acompletion",
        AsyncMock(side_effect=Exception(f"bad auth {secret}")),
    )

    resp = client_no_provider.post(
        "/api/v1/status/test",
        headers={"X-Provider-Name": "openai", "X-Provider-Key": secret},
    )

    assert secret not in resp.text


# ---------------------------------------------------------------------------
# compare and batch also accept judge_model
# ---------------------------------------------------------------------------


def test_compare_accepts_judge_model(client_no_provider: TestClient, mocker: Any) -> None:
    """compare endpoint passes judge_model override to the grader."""
    mocker.patch("litellm.acompletion", AsyncMock(return_value=_mock_llm_response(_VALID_JSON)))

    resp = client_no_provider.post(
        "/api/v1/compare",
        json={
            "prompt_a": "Explain Python.",
            "prompt_b": "Describe Python briefly.",
            "grader": "llm_judge",
            "judge_model": "ollama/llama3",
        },
        headers={"X-Provider-Name": "anthropic", "X-Provider-Key": "sk-test"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["winner"] in ("a", "b", "tie")


def test_batch_accepts_judge_model(client_no_provider: TestClient, mocker: Any) -> None:
    """batch endpoint passes judge_model override to the grader."""
    mocker.patch("litellm.acompletion", AsyncMock(return_value=_mock_llm_response(_VALID_JSON)))

    resp = client_no_provider.post(
        "/api/v1/batch",
        json={
            "items": [{"id": "1", "prompt": "Write a haiku about AI."}],
            "grader": "llm_judge",
            "judge_model": "ollama/mistral",
        },
        headers={"X-Provider-Name": "anthropic", "X-Provider-Key": "sk-test"},
    )

    assert resp.status_code == 200
    lines = [l for l in resp.text.strip().split("\n") if l]
    assert len(lines) == 1
    import json as _json
    row = _json.loads(lines[0])
    assert "result" in row
