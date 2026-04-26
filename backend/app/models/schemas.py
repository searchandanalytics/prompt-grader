"""Pydantic v2 schemas shared across API and domain layers."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class GraderType(str, Enum):
    """Available grader implementations."""

    rule_based = "rule_based"
    llm_judge = "llm_judge"
    hybrid = "hybrid"


class JudgeProvider(str, Enum):
    """Supported LLM judge providers."""

    anthropic = "anthropic"
    openai = "openai"
    google = "google"
    groq = "groq"
    ollama = "ollama"
    none = "none"  # rule-based only mode


# ---------------------------------------------------------------------------
# Provider config (per-request, carries optional UI-supplied key)
# ---------------------------------------------------------------------------

KeySource = Literal["ui_session", "ui_persisted", "env", "ollama_auto", "rule_based"]


class ProviderConfig(BaseModel):
    """Resolved judge provider for a single request.

    ``api_key`` is the UI-supplied key from the request header — never logged,
    never persisted, used once then discarded.
    """

    provider: str
    model: str | None = None
    api_key: str | None = Field(default=None, exclude=True)  # never serialised
    key_source: KeySource = "rule_based"


# ---------------------------------------------------------------------------
# Rubric
# ---------------------------------------------------------------------------


class RubricCriteria(BaseModel):
    """Weight + description for a single rubric dimension."""

    weight: float = Field(ge=0.0, le=1.0)
    description: str = ""


class Rubric(BaseModel):
    """Defines what 'good' means for a prompt across 5 dimensions."""

    clarity: RubricCriteria = RubricCriteria(weight=0.20, description="Is the prompt clear and unambiguous?")
    specificity: RubricCriteria = RubricCriteria(weight=0.20, description="Does the prompt provide enough specific detail?")
    structure: RubricCriteria = RubricCriteria(weight=0.20, description="Is the prompt well-structured and logically ordered?")
    task_alignment: RubricCriteria = RubricCriteria(weight=0.20, description="Does the prompt align with the intended task?")
    safety: RubricCriteria = RubricCriteria(weight=0.20, description="Is the prompt free of harmful or unsafe content?")

    def total_weight(self) -> float:
        """Return sum of all criterion weights."""
        return (
            self.clarity.weight
            + self.specificity.weight
            + self.structure.weight
            + self.task_alignment.weight
            + self.safety.weight
        )


# ---------------------------------------------------------------------------
# Grade result
# ---------------------------------------------------------------------------


class GradeResult(BaseModel):
    """Output from any grader."""

    score: float = Field(ge=0.0, le=100.0, description="Overall score 0-100.")
    breakdown: dict[str, float] = Field(
        default_factory=dict,
        description="Per-dimension sub-scores (0-100 each).",
    )
    feedback: str = Field(default="", description="Human-readable feedback.")
    grader: GraderType
    provider: JudgeProvider = JudgeProvider.none
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# API request/response models
# ---------------------------------------------------------------------------


class GradeRequest(BaseModel):
    """Single-prompt grading request."""

    prompt: str = Field(min_length=1, max_length=32_000)
    rubric: Rubric = Field(default_factory=Rubric)
    grader: GraderType = GraderType.hybrid
    judge_model: str | None = Field(default=None, description="Override the LLM judge model (e.g. an Ollama model name).")


class GradeResponse(BaseModel):
    """Single-prompt grading response."""

    prompt: str
    result: GradeResult


class CompareRequest(BaseModel):
    """Side-by-side comparison of two prompts."""

    prompt_a: str = Field(min_length=1, max_length=32_000)
    prompt_b: str = Field(min_length=1, max_length=32_000)
    rubric: Rubric = Field(default_factory=Rubric)
    grader: GraderType = GraderType.hybrid
    judge_model: str | None = Field(default=None, description="Override the LLM judge model.")


class CompareResponse(BaseModel):
    """Side-by-side comparison result."""

    prompt_a: str
    prompt_b: str
    result_a: GradeResult
    result_b: GradeResult
    winner: str = Field(description="'a', 'b', or 'tie'")


class BatchItem(BaseModel):
    """One item in a batch grading request."""

    id: str = ""
    prompt: str = Field(min_length=1, max_length=32_000)


class BatchRequest(BaseModel):
    """Batch grading request (JSON body variant)."""

    items: list[BatchItem]
    rubric: Rubric = Field(default_factory=Rubric)
    grader: GraderType = GraderType.hybrid
    judge_model: str | None = Field(default=None, description="Override the LLM judge model.")


class BatchResultItem(BaseModel):
    """Result for one item in a batch."""

    id: str
    prompt: str
    result: GradeResult


class StatusResponse(BaseModel):
    """Backend status including active judge configuration."""

    status: str = "ok"
    judge_provider: JudgeProvider
    judge_model: str | None
    mode: str = Field(description="'rule_based', 'llm', or 'hybrid'")
    key_source: KeySource = "rule_based"
    unhealthy_reason: str | None = Field(
        default=None,
        description=(
            "Set when the previously active provider was unreachable and the "
            "server fell back to a different one. Null when healthy."
        ),
    )


class TestConnectionResponse(BaseModel):
    """Result of a provider connectivity test."""

    ok: bool
    provider: str
    model: str | None = None
    latency_ms: float | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Prompt Builder (Feature 2) — CO-STAR wizard
# ---------------------------------------------------------------------------


class PromptStyle(str, Enum):
    """Writing style options for the prompt builder."""

    formal = "formal"
    casual = "casual"
    technical = "technical"
    creative = "creative"


class PromptTone(str, Enum):
    """Tone options for the prompt builder."""

    friendly = "friendly"
    authoritative = "authoritative"
    playful = "playful"
    empathetic = "empathetic"
    neutral = "neutral"


class ResponseFormat(str, Enum):
    """Expected output format options."""

    paragraph = "paragraph"
    bulleted_list = "bulleted_list"
    json = "json"
    table = "table"
    markdown = "markdown"
    code = "code"


class PromptBlueprint(BaseModel):
    """User answers collected by the 9-step wizard.

    Required fields map to wizard steps 1, 3, 4, 5, 6.
    Optional fields map to steps 2, 7, 8 (skippable).
    """

    # Step 1 — required
    task: str = Field(min_length=1, max_length=2_000, description="What the AI should do.")
    # Step 2 — optional
    context: str | None = Field(default=None, max_length=2_000, description="Background the AI needs.")
    # Step 3 — required
    objective: str = Field(min_length=1, max_length=2_000, description="What success looks like.")
    # Step 4 — required
    style: PromptStyle = PromptStyle.formal
    tone: PromptTone = PromptTone.neutral
    # Step 5 — required
    audience: str = Field(min_length=1, max_length=500, description="Who the output is for.")
    # Step 6 — required
    response_format: ResponseFormat = ResponseFormat.paragraph
    length: str | None = Field(default=None, max_length=200, description="Optional length hint, e.g. 'under 50 words'.")
    # Step 7 — optional
    examples: str | None = Field(default=None, max_length=4_000, description="1-3 examples of ideal output.")
    # Step 8 — optional
    constraints: str | None = Field(default=None, max_length=2_000, description="Things to avoid or must-haves.")


class BuildResponse(BaseModel):
    """Result from the prompt builder endpoint."""

    prompt: str = Field(description="The generated production-ready prompt.")
    explanation: str = Field(description="Brief description of how the prompt was constructed.")
    generated_by: Literal["llm", "template"] = Field(
        description="'llm' when an LLM generated the prompt; 'template' for offline fallback."
    )
    grade_result: GradeResult | None = Field(
        default=None,
        description="Auto-graded result for the generated prompt (null if grading unavailable).",
    )
