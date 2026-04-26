"""Domain exceptions for PromptGrade."""


class PromptGradeError(Exception):
    """Base exception for all domain errors."""


class GraderNotFoundError(PromptGradeError):
    """Raised when a requested grader type does not exist."""


class RubricValidationError(PromptGradeError):
    """Raised when a rubric fails validation."""


class LLMProviderError(PromptGradeError):
    """Raised when an LLM provider call fails."""


class ProviderNotConfiguredError(PromptGradeError):
    """Raised when no LLM provider is available and LLM grading is requested."""
