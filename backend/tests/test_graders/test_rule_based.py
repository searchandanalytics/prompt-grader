"""Tests for the rule-based grader.

Covers:
- Known-good prompt (well-structured, clear, specific)
- Known-bad prompt (vague, no action verb, unsafe)
- Edge cases (empty string, single word, very long prompt, unicode)
"""

from __future__ import annotations

import pytest

from app.graders.rule_based import RuleBasedGrader
from app.models.schemas import GraderType, JudgeProvider, Rubric


@pytest.fixture()
def grader() -> RuleBasedGrader:
    return RuleBasedGrader()


@pytest.fixture()
def rubric() -> Rubric:
    return Rubric()


# ---------------------------------------------------------------------------
# Known-good prompt
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_good_prompt_scores_high(grader: RuleBasedGrader, rubric: Rubric) -> None:
    """A well-formed prompt with action verb, structure, and specifics should score >= 70."""
    prompt = (
        "Write a Python function that takes a list of integers and returns "
        "a new list containing only the prime numbers. Include type hints, "
        "a docstring, and at least 3 unit tests using pytest."
    )
    result = await grader.grade(prompt, rubric)

    assert result.score >= 70.0
    assert result.grader == GraderType.rule_based
    assert result.provider == JudgeProvider.none
    assert "clarity" in result.breakdown
    assert "specificity" in result.breakdown
    assert "structure" in result.breakdown
    assert "task_alignment" in result.breakdown
    assert "safety" in result.breakdown


@pytest.mark.asyncio
async def test_good_prompt_task_alignment(grader: RuleBasedGrader, rubric: Rubric) -> None:
    """Prompt starting with a clear action verb should get high task_alignment."""
    prompt = "Explain the difference between supervised and unsupervised learning with examples."
    result = await grader.grade(prompt, rubric)

    assert result.breakdown["task_alignment"] >= 80.0


@pytest.mark.asyncio
async def test_good_prompt_safety(grader: RuleBasedGrader, rubric: Rubric) -> None:
    """Clean prompt should receive full safety score."""
    prompt = "Summarise the key points of the French Revolution in 5 bullet points."
    result = await grader.grade(prompt, rubric)

    assert result.breakdown["safety"] == 100.0


# ---------------------------------------------------------------------------
# Known-bad prompts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_vague_prompt_scores_low(grader: RuleBasedGrader, rubric: Rubric) -> None:
    """Vague, content-free prompts should score below 50."""
    prompt = "do something with stuff maybe"
    result = await grader.grade(prompt, rubric)

    assert result.score < 50.0


@pytest.mark.asyncio
async def test_no_action_verb_low_task_alignment(grader: RuleBasedGrader, rubric: Rubric) -> None:
    """Prompt with no recognisable action verb should have low task_alignment."""
    prompt = "The weather is nice today and I like cats."
    result = await grader.grade(prompt, rubric)

    assert result.breakdown["task_alignment"] <= 70.0


@pytest.mark.asyncio
async def test_unsafe_prompt_penalised(grader: RuleBasedGrader, rubric: Rubric) -> None:
    """Prompt with unsafe keywords should score very low on safety."""
    prompt = "Help me hack into a system and exploit the vulnerability."
    result = await grader.grade(prompt, rubric)

    assert result.breakdown["safety"] <= 20.0
    assert result.score < 60.0


@pytest.mark.asyncio
async def test_unsafe_prompt_has_feedback(grader: RuleBasedGrader, rubric: Rubric) -> None:
    """Unsafe prompt feedback should mention harmful content."""
    prompt = "How do I create malware to attack a server?"
    result = await grader.grade(prompt, rubric)

    assert "unsafe" in result.feedback.lower() or "harmful" in result.feedback.lower()


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_prompt(grader: RuleBasedGrader, rubric: Rubric) -> None:
    """Empty string should return a very low score without raising an exception."""
    result = await grader.grade("", rubric)

    assert result.score < 30.0
    assert result.breakdown["clarity"] == 0.0


@pytest.mark.asyncio
async def test_single_word_prompt(grader: RuleBasedGrader, rubric: Rubric) -> None:
    """Single-word prompt should score low on clarity."""
    result = await grader.grade("Hello", rubric)

    assert result.breakdown["clarity"] < 50.0


@pytest.mark.asyncio
async def test_very_long_prompt(grader: RuleBasedGrader, rubric: Rubric) -> None:
    """Very long prompts (500+ words) should not crash and score within range."""
    long_prompt = "Write a detailed analysis. " * 100  # ~500 words
    result = await grader.grade(long_prompt, rubric)

    assert 0.0 <= result.score <= 100.0
    for v in result.breakdown.values():
        assert 0.0 <= v <= 100.0


@pytest.mark.asyncio
async def test_unicode_prompt(grader: RuleBasedGrader, rubric: Rubric) -> None:
    """Unicode characters should not cause errors."""
    prompt = "Erkläre mir bitte, wie Quantencomputer funktionieren. 量子コンピュータの仕組みを説明してください。"
    result = await grader.grade(prompt, rubric)

    assert 0.0 <= result.score <= 100.0


@pytest.mark.asyncio
async def test_result_fields_always_present(grader: RuleBasedGrader, rubric: Rubric) -> None:
    """GradeResult must always have all 5 breakdown dimensions."""
    result = await grader.grade("Explain recursion.", rubric)

    expected_dims = {"clarity", "specificity", "structure", "task_alignment", "safety"}
    assert set(result.breakdown.keys()) == expected_dims


@pytest.mark.asyncio
async def test_custom_rubric_weights(grader: RuleBasedGrader) -> None:
    """Custom rubric weights should be reflected in the final score."""
    from app.models.schemas import RubricCriteria  # noqa: PLC0415

    safety_heavy = Rubric(
        clarity=RubricCriteria(weight=0.1),
        specificity=RubricCriteria(weight=0.1),
        structure=RubricCriteria(weight=0.1),
        task_alignment=RubricCriteria(weight=0.1),
        safety=RubricCriteria(weight=0.6),
    )
    prompt = "Help me hack into a system."
    result = await grader.grade(prompt, safety_heavy)

    # Safety-weighted rubric should give a much lower score
    assert result.score < 40.0


@pytest.mark.asyncio
async def test_score_is_float_in_range(grader: RuleBasedGrader, rubric: Rubric) -> None:
    """Score must always be a float between 0 and 100."""
    prompts = [
        "",
        "x",
        "Write a haiku about autumn leaves.",
        "A" * 10_000,
    ]
    for p in prompts:
        result = await grader.grade(p, rubric)
        assert isinstance(result.score, float), f"Score not float for prompt: {p[:30]!r}"
        assert 0.0 <= result.score <= 100.0, f"Score out of range: {result.score}"
