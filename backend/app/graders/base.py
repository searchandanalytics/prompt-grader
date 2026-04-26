"""Abstract base class for all PromptGrade graders."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.schemas import GradeResult, Rubric


class Grader(ABC):
    """Contract that every grader implementation must satisfy."""

    @abstractmethod
    async def grade(self, prompt: str, rubric: Rubric) -> GradeResult:
        """Evaluate *prompt* against *rubric* and return a GradeResult.

        Args:
            prompt: The prompt text to evaluate.
            rubric: Weighted criteria defining what 'good' looks like.

        Returns:
            A GradeResult with score (0-100), breakdown, and feedback.
        """
