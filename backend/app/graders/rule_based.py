"""Rule-based grader — fast, deterministic, zero API cost."""

from __future__ import annotations

import re

from app.graders.base import Grader
from app.models.schemas import GradeResult, GraderType, JudgeProvider, Rubric

# Vague / filler words that reduce clarity score
_VAGUE_WORDS = frozenset(
    {
        "something", "stuff", "things", "whatever", "somehow", "maybe",
        "perhaps", "probably", "kind of", "sort of", "etc", "and so on",
    }
)

# Common structure indicators
_STRUCTURE_MARKERS = re.compile(
    r"(\b(step|first|second|third|finally|then|next|lastly)\b"
    r"|\b\d+[\.\)]\s"
    r"|[-*•]\s)",
    re.IGNORECASE,
)

# Potentially unsafe / harmful signal words
_UNSAFE_PATTERNS = re.compile(
    r"\b(hack|exploit|bypass|illegal|weapon|malware|phishing|jailbreak"
    r"|kill|harm|attack|bomb|drug\s+synthesis)\b",
    re.IGNORECASE,
)


def _clarity_score(prompt: str) -> float:
    """Score 0-100 based on length, vague words, and question marks."""
    words = prompt.split()
    word_count = len(words)

    if word_count == 0:
        return 0.0

    # Penalise very short or very long prompts
    length_score: float
    if word_count < 5:
        length_score = 20.0
    elif word_count < 10:
        length_score = 50.0
    elif word_count <= 200:
        length_score = 100.0
    elif word_count <= 500:
        length_score = 80.0
    else:
        length_score = 60.0

    # Penalise vague words
    lower_words = [w.lower().strip(".,!?;:") for w in words]
    vague_count = sum(1 for w in lower_words if w in _VAGUE_WORDS)
    vague_penalty = min(vague_count * 10, 40)

    return max(0.0, length_score - vague_penalty)


def _specificity_score(prompt: str) -> float:
    """Score 0-100 based on presence of concrete details."""
    words = prompt.split()
    if not words:
        return 0.0

    score = 40.0

    # Numbers / quantities suggest specificity
    if re.search(r"\b\d+\b", prompt):
        score += 20.0

    # Named entities or proper nouns (simple heuristic: Title Case words)
    title_case_words = re.findall(r"\b[A-Z][a-z]{2,}\b", prompt)
    if len(title_case_words) >= 2:
        score += 20.0

    # Code blocks or backticks
    if "`" in prompt or "```" in prompt:
        score += 10.0

    # Quoted strings suggest concrete examples
    if re.search(r'["\']', prompt):
        score += 10.0

    # Penalise vague filler words
    lower_words = [w.lower().strip(".,!?;:") for w in words]
    vague_count = sum(1 for w in lower_words if w in _VAGUE_WORDS)
    score -= min(vague_count * 10, 30)

    return max(0.0, min(score, 100.0))


def _structure_score(prompt: str) -> float:
    """Score 0-100 based on logical organisation signals."""
    if not prompt.strip():
        return 0.0
    score = 40.0

    # Ordered/unordered list markers or transition words
    marker_count = len(_STRUCTURE_MARKERS.findall(prompt))
    score += min(marker_count * 15, 40)

    # Has a clear ending punctuation
    if prompt.rstrip().endswith((".", "?", "!")):
        score += 10.0

    # Multi-sentence prompts show more structure
    sentences = re.split(r"[.!?]+", prompt)
    if len(sentences) >= 3:
        score += 10.0

    return min(score, 100.0)


def _task_alignment_score(prompt: str) -> float:
    """Score 0-100 based on presence of a clear action verb."""
    if not prompt.strip():
        return 0.0
    action_verbs = re.compile(
        r"\b(write|create|generate|explain|describe|list|summarise|summarize"
        r"|analyse|analyze|compare|translate|convert|fix|review|improve"
        r"|suggest|identify|classify|extract|draft|outline|evaluate)\b",
        re.IGNORECASE,
    )
    if action_verbs.search(prompt):
        return 90.0

    # Softer signal: ends with a question mark
    if prompt.strip().endswith("?"):
        return 70.0

    return 40.0


def _safety_score(prompt: str) -> float:
    """Score 0-100; deducts heavily for unsafe signal words."""
    if _UNSAFE_PATTERNS.search(prompt):
        return 10.0
    return 100.0


class RuleBasedGrader(Grader):
    """Deterministic grader using heuristic rules — no LLM required."""

    async def grade(self, prompt: str, rubric: Rubric) -> GradeResult:
        """Grade *prompt* using rule-based heuristics.

        Args:
            prompt: The prompt text to evaluate.
            rubric: Criteria weights (only weights are used; descriptions ignored).

        Returns:
            GradeResult with per-dimension breakdown and weighted overall score.
        """
        breakdown = {
            "clarity": _clarity_score(prompt),
            "specificity": _specificity_score(prompt),
            "structure": _structure_score(prompt),
            "task_alignment": _task_alignment_score(prompt),
            "safety": _safety_score(prompt),
        }

        weights = {
            "clarity": rubric.clarity.weight,
            "specificity": rubric.specificity.weight,
            "structure": rubric.structure.weight,
            "task_alignment": rubric.task_alignment.weight,
            "safety": rubric.safety.weight,
        }

        total_weight = sum(weights.values()) or 1.0
        score = sum(breakdown[k] * weights[k] for k in breakdown) / total_weight

        feedback_parts: list[str] = []
        if breakdown["clarity"] < 50:
            feedback_parts.append("Prompt is too vague or too short — add more detail.")
        if breakdown["specificity"] < 50:
            feedback_parts.append("Add concrete examples, numbers, or named entities.")
        if breakdown["structure"] < 50:
            feedback_parts.append("Consider using numbered steps or clear transitions.")
        if breakdown["task_alignment"] < 50:
            feedback_parts.append("Start with a clear action verb (e.g. 'Write', 'Explain', 'List').")
        if breakdown["safety"] < 50:
            feedback_parts.append("Prompt contains potentially unsafe content.")

        feedback = " ".join(feedback_parts) if feedback_parts else "Prompt looks solid."

        return GradeResult(
            score=round(score, 2),
            breakdown={k: round(v, 2) for k, v in breakdown.items()},
            feedback=feedback,
            grader=GraderType.rule_based,
            provider=JudgeProvider.none,
        )
