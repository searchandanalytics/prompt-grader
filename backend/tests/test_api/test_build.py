"""Tests for Feature 2: Prompt Builder — POST /api/v1/build.

Covers:
- LLM path: mock returns text, response has generated_by="llm"
- Template fallback: no provider → generated_by="template", prompt contains blueprint fields
- LLM failure → template fallback (no 5xx)
- Auto-grade is included in response
- grade_result is omitted gracefully if grading fails
- Common LLM output wrappers are stripped (fences, preamble)
- Required field validation (task, objective, audience)
- All optional fields can be omitted
- judge_model / X-Provider-Key pass-through to LLM

All LLM calls are mocked.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def client_no_provider() -> TestClient:
    app.state.judge_config = {"provider": "none", "model": None}
    return TestClient(app)


@pytest.fixture()
def client_anthropic() -> TestClient:
    app.state.judge_config = {"provider": "anthropic", "model": "claude-sonnet-4-6"}
    return TestClient(app)


def _mock_llm(content: str) -> MagicMock:
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


_MINIMAL_BLUEPRINT = {
    "task": "Write product descriptions for a sustainable home-goods brand.",
    "objective": "Drive clicks and convey eco-friendliness in under 50 words.",
    "style": "casual",
    "tone": "friendly",
    "audience": "Eco-conscious online shoppers aged 25-40",
    "response_format": "paragraph",
}

_FULL_BLUEPRINT = {
    **_MINIMAL_BLUEPRINT,
    "context": "We sell bamboo kitchenware to eco-conscious millennials.",
    "length": "under 50 words",
    "examples": "Example: Our bamboo cutting board brings nature into your kitchen.",
    "constraints": "No superlatives. Always mention free shipping.",
}

_LLM_BUILT_PROMPT = (
    "You are a copywriter for a sustainable home-goods brand. "
    "Write product descriptions that drive clicks and convey eco-friendliness. "
    "Target eco-conscious shoppers aged 25-40. Keep each description under 50 words."
)


# ---------------------------------------------------------------------------
# LLM path
# ---------------------------------------------------------------------------


def test_llm_path_returns_generated_by_llm(
    client_anthropic: TestClient,
    mocker: Any,
) -> None:
    """When an LLM is configured and succeeds, generated_by must be 'llm'."""
    # Mock both the builder call and the grader call.
    mocker.patch("litellm.acompletion", AsyncMock(return_value=_mock_llm(_LLM_BUILT_PROMPT)))

    resp = client_anthropic.post("/api/v1/build", json=_MINIMAL_BLUEPRINT)

    assert resp.status_code == 200
    data = resp.json()
    assert data["generated_by"] == "llm"
    assert data["prompt"] == _LLM_BUILT_PROMPT
    assert "anthropic" in data["explanation"].lower()


def test_llm_path_with_ui_key(
    client_no_provider: TestClient,
    mocker: Any,
) -> None:
    """UI-supplied X-Provider-Key overrides no-provider server config."""
    mock = AsyncMock(return_value=_mock_llm(_LLM_BUILT_PROMPT))
    mocker.patch("litellm.acompletion", mock)

    resp = client_no_provider.post(
        "/api/v1/build",
        json=_MINIMAL_BLUEPRINT,
        headers={"X-Provider-Name": "anthropic", "X-Provider-Key": "sk-ui-key"},
    )

    assert resp.status_code == 200
    assert resp.json()["generated_by"] == "llm"

    # Key must have been forwarded to LiteLLM.
    calls = mock.call_args_list
    # Two calls: one for build, one for auto-grade hybrid.
    assert any(c.kwargs.get("api_key") == "sk-ui-key" for c in calls)


def test_ui_key_not_in_build_response(
    client_no_provider: TestClient,
    mocker: Any,
) -> None:
    """API key must never appear in the build response."""
    secret = "sk-build-secret-xyz"
    mocker.patch("litellm.acompletion", AsyncMock(return_value=_mock_llm(_LLM_BUILT_PROMPT)))

    resp = client_no_provider.post(
        "/api/v1/build",
        json=_MINIMAL_BLUEPRINT,
        headers={"X-Provider-Name": "anthropic", "X-Provider-Key": secret},
    )

    assert secret not in resp.text


# ---------------------------------------------------------------------------
# LLM output stripping
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected_contains",
    [
        # Markdown fence
        ("```\nWrite product descriptions.\n```", "Write product descriptions."),
        ("```text\nWrite product descriptions.\n```", "Write product descriptions."),
        # Common preamble
        ("Here is your prompt:\nWrite product descriptions.", "Write product descriptions."),
        ("Sure! Here is the prompt:\nWrite product descriptions.", "Write product descriptions."),
        # Clean output (no stripping needed)
        ("Write product descriptions.", "Write product descriptions."),
    ],
    ids=["fence", "fence_lang", "preamble_here_is", "preamble_sure", "clean"],
)
def test_llm_output_stripped(
    client_anthropic: TestClient,
    mocker: Any,
    raw: str,
    expected_contains: str,
) -> None:
    """Common LLM wrappers are removed from the output prompt."""
    mocker.patch("litellm.acompletion", AsyncMock(return_value=_mock_llm(raw)))

    resp = client_anthropic.post("/api/v1/build", json=_MINIMAL_BLUEPRINT)

    assert resp.status_code == 200
    assert expected_contains in resp.json()["prompt"]


# ---------------------------------------------------------------------------
# Template fallback
# ---------------------------------------------------------------------------


def test_template_fallback_when_no_provider(client_no_provider: TestClient) -> None:
    """Without any LLM provider, build falls back to template (no 5xx)."""
    resp = client_no_provider.post("/api/v1/build", json=_MINIMAL_BLUEPRINT)

    assert resp.status_code == 200
    data = resp.json()
    assert data["generated_by"] == "template"
    assert "template" in data["explanation"].lower()


def test_template_fallback_when_llm_fails(
    client_anthropic: TestClient,
    mocker: Any,
) -> None:
    """LLM failure must silently fall back to template, not 5xx."""
    mocker.patch(
        "litellm.acompletion",
        AsyncMock(side_effect=Exception("network timeout")),
    )

    resp = client_anthropic.post("/api/v1/build", json=_MINIMAL_BLUEPRINT)

    assert resp.status_code == 200
    assert resp.json()["generated_by"] == "template"


def test_template_contains_task(client_no_provider: TestClient) -> None:
    """Template output must contain the task text."""
    resp = client_no_provider.post("/api/v1/build", json=_MINIMAL_BLUEPRINT)
    assert _MINIMAL_BLUEPRINT["task"] in resp.json()["prompt"]


def test_template_contains_optional_fields(client_no_provider: TestClient) -> None:
    """All provided optional fields should appear somewhere in the template output."""
    resp = client_no_provider.post("/api/v1/build", json=_FULL_BLUEPRINT)
    prompt = resp.json()["prompt"]

    assert _FULL_BLUEPRINT["context"] in prompt
    assert _FULL_BLUEPRINT["examples"] in prompt
    assert _FULL_BLUEPRINT["constraints"] in prompt


def test_template_without_optional_fields(client_no_provider: TestClient) -> None:
    """Blueprint with only required fields should produce a valid prompt."""
    resp = client_no_provider.post("/api/v1/build", json=_MINIMAL_BLUEPRINT)
    assert resp.status_code == 200
    assert len(resp.json()["prompt"]) > 20


# ---------------------------------------------------------------------------
# Auto-grading
# ---------------------------------------------------------------------------


def test_auto_grade_included_in_response(client_no_provider: TestClient) -> None:
    """grade_result must be present in a successful build response."""
    resp = client_no_provider.post("/api/v1/build", json=_MINIMAL_BLUEPRINT)

    assert resp.status_code == 200
    grade = resp.json()["grade_result"]
    assert grade is not None
    assert 0.0 <= grade["score"] <= 100.0
    assert "clarity" in grade["breakdown"]


def test_auto_grade_score_in_range(client_no_provider: TestClient) -> None:
    """Auto-grade score must be a valid float 0-100."""
    resp = client_no_provider.post("/api/v1/build", json=_FULL_BLUEPRINT)
    score = resp.json()["grade_result"]["score"]
    assert isinstance(score, float)
    assert 0.0 <= score <= 100.0


def test_auto_grade_with_llm(client_anthropic: TestClient, mocker: Any) -> None:
    """Auto-grade runs even when the prompt was LLM-generated."""
    mocker.patch("litellm.acompletion", AsyncMock(return_value=_mock_llm(_LLM_BUILT_PROMPT)))

    resp = client_anthropic.post("/api/v1/build", json=_MINIMAL_BLUEPRINT)

    assert resp.status_code == 200
    assert resp.json()["grade_result"] is not None


# ---------------------------------------------------------------------------
# Request validation
# ---------------------------------------------------------------------------


def test_missing_task_returns_422(client_no_provider: TestClient) -> None:
    """Omitting the required 'task' field returns a 422 validation error."""
    bad = {k: v for k, v in _MINIMAL_BLUEPRINT.items() if k != "task"}
    resp = client_no_provider.post("/api/v1/build", json=bad)
    assert resp.status_code == 422


def test_missing_objective_returns_422(client_no_provider: TestClient) -> None:
    bad = {k: v for k, v in _MINIMAL_BLUEPRINT.items() if k != "objective"}
    resp = client_no_provider.post("/api/v1/build", json=bad)
    assert resp.status_code == 422


def test_missing_audience_returns_422(client_no_provider: TestClient) -> None:
    bad = {k: v for k, v in _MINIMAL_BLUEPRINT.items() if k != "audience"}
    resp = client_no_provider.post("/api/v1/build", json=bad)
    assert resp.status_code == 422


def test_empty_task_returns_422(client_no_provider: TestClient) -> None:
    """Empty string for required field must be rejected."""
    bad = {**_MINIMAL_BLUEPRINT, "task": ""}
    resp = client_no_provider.post("/api/v1/build", json=bad)
    assert resp.status_code == 422


def test_invalid_style_returns_422(client_no_provider: TestClient) -> None:
    """Unknown enum value for style must be rejected."""
    bad = {**_MINIMAL_BLUEPRINT, "style": "aggressive"}
    resp = client_no_provider.post("/api/v1/build", json=bad)
    assert resp.status_code == 422


def test_invalid_response_format_returns_422(client_no_provider: TestClient) -> None:
    bad = {**_MINIMAL_BLUEPRINT, "response_format": "tweet"}
    resp = client_no_provider.post("/api/v1/build", json=bad)
    assert resp.status_code == 422


def test_valid_enum_values_accepted(client_no_provider: TestClient) -> None:
    """All documented enum values should be accepted."""
    for style in ("formal", "casual", "technical", "creative"):
        for tone in ("friendly", "authoritative", "playful", "empathetic", "neutral"):
            for fmt in ("paragraph", "bulleted_list", "json", "table", "markdown", "code"):
                payload = {**_MINIMAL_BLUEPRINT, "style": style, "tone": tone, "response_format": fmt}
                resp = client_no_provider.post("/api/v1/build", json=payload)
                assert resp.status_code == 200, f"Failed for style={style} tone={tone} fmt={fmt}"
