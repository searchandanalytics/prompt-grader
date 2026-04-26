"""Prompt Builder service — assembles or LLM-generates prompts from a PromptBlueprint.

Two code paths:
- ``build_with_llm``: calls the configured LLM with a CO-STAR meta-prompt.
  Returns the LLM output after stripping any surrounding prose or markdown.
- ``build_with_template``: pure string assembly, works fully offline.
  Falls back to this whenever no LLM is configured or the LLM call fails.
"""

from __future__ import annotations

import logging
import re

import litellm  # type: ignore[import-untyped]

from app.core.exceptions import LLMProviderError, ProviderNotConfiguredError
from app.models.schemas import PromptBlueprint, ProviderConfig, ResponseFormat

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CO-STAR LLM meta-prompt
# ---------------------------------------------------------------------------

_BUILD_SYSTEM_PROMPT = """\
You are an expert prompt engineer. Your sole job is to write production-ready prompts.

Given a user's blueprint, construct a single, self-contained prompt following the CO-STAR framework:
  C — Context:    background the AI needs to know
  O — Objective:  what the AI must accomplish and what success looks like
  S — Style:      the writing style the AI should adopt
  T — Tone:       the emotional register the AI should use
  A — Audience:   who the AI is writing for
  R — Response:   the expected output format

Rules:
- Output ONLY the final prompt text, nothing else.
- Do NOT include preamble such as "Here is your prompt:" or "Sure!".
- Do NOT wrap the prompt in markdown fences.
- Integrate all provided blueprint fields naturally — do not just list them.
- If examples are provided, weave them into the prompt with "For example:" or an Examples section.
- If constraints are provided, include them as clear instructions within the prompt.
"""


def _blueprint_to_user_message(blueprint: PromptBlueprint) -> str:
    """Serialise the blueprint into a structured message for the LLM."""
    lines = [
        f"Task: {blueprint.task}",
        f"Objective: {blueprint.objective}",
        f"Style: {blueprint.style.value}",
        f"Tone: {blueprint.tone.value}",
        f"Audience: {blueprint.audience}",
        f"Response format: {blueprint.response_format.value.replace('_', ' ')}",
    ]
    if blueprint.context:
        lines.insert(0, f"Context: {blueprint.context}")
    if blueprint.length:
        lines.append(f"Length target: {blueprint.length}")
    if blueprint.examples:
        lines.append(f"Examples of ideal output:\n{blueprint.examples}")
    if blueprint.constraints:
        lines.append(f"Constraints:\n{blueprint.constraints}")
    return "\n".join(lines)


def _strip_llm_wrapper(raw: str) -> str:
    """Remove common LLM preamble/postamble and markdown fences from the output.

    Some models add "Here is your prompt:" or wrap the text in ```...``` despite
    the system instruction.  Strip these so the returned string is a clean prompt.
    """
    text = raw.strip()

    # Strip markdown code fences (``` or ```text or ```prompt etc.)
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        text = text.rsplit("```", 1)[0]
        text = text.strip()

    # Strip common one-line preambles ("Here is your prompt:\n", "Sure!\n", etc.)
    preamble_re = re.compile(
        r"^(here is|sure[,!]?|of course[,!]?|here['']s|below is|the following is)[^\n]*\n+",
        re.IGNORECASE,
    )
    text = preamble_re.sub("", text).strip()

    return text


# ---------------------------------------------------------------------------
# LLM path
# ---------------------------------------------------------------------------


async def build_with_llm(
    blueprint: PromptBlueprint,
    provider_config: ProviderConfig,
) -> str:
    """Generate a prompt using the configured LLM.

    Args:
        blueprint: The user's wizard answers.
        provider_config: Resolved provider config for this request.

    Returns:
        The generated prompt string (preamble/fences stripped).

    Raises:
        ProviderNotConfiguredError: If no LLM provider is available.
        LLMProviderError: If the LLM call fails.
    """
    provider = provider_config.provider
    model = provider_config.model
    api_key = provider_config.api_key

    if not provider or provider == "none":
        raise ProviderNotConfiguredError(
            "No LLM provider configured. Using template-based prompt assembly."
        )

    extra: dict[str, object] = {}
    if api_key:
        extra["api_key"] = api_key

    try:
        response = await litellm.acompletion(
            model=model or provider,
            messages=[
                {"role": "system", "content": _BUILD_SYSTEM_PROMPT},
                {"role": "user", "content": _blueprint_to_user_message(blueprint)},
            ],
            temperature=0.4,  # slight creativity for prompt writing
            max_tokens=1_024,
            **extra,
        )
    except Exception as exc:
        safe_msg = str(exc)
        if api_key:
            safe_msg = safe_msg.replace(api_key, "***REDACTED***")
        logger.error("Prompt builder LLM call failed: %s", safe_msg)
        raise LLMProviderError(safe_msg) from exc

    raw = response.choices[0].message.content or ""
    if not raw.strip():
        raise LLMProviderError("LLM returned an empty response for prompt building.")

    return _strip_llm_wrapper(raw)


# ---------------------------------------------------------------------------
# Template path (offline fallback)
# ---------------------------------------------------------------------------

_FORMAT_LABELS: dict[ResponseFormat, str] = {
    ResponseFormat.paragraph: "one or more paragraphs",
    ResponseFormat.bulleted_list: "a bulleted list",
    ResponseFormat.json: "valid JSON",
    ResponseFormat.table: "a markdown table",
    ResponseFormat.markdown: "formatted markdown",
    ResponseFormat.code: "a code block with the appropriate language tag",
}


def build_with_template(blueprint: PromptBlueprint) -> str:
    """Assemble a structured prompt from the blueprint without any LLM.

    Uses a CO-STAR-inspired section layout.  Works fully offline and
    is always deterministic for the same input.

    Args:
        blueprint: The user's wizard answers.

    Returns:
        A multi-section prompt string ready to copy into an AI interface.
    """
    sections: list[str] = []

    # --- Context (optional) ---
    if blueprint.context:
        sections.append(f"## Context\n{blueprint.context}")

    # --- Task + Objective ---
    sections.append(f"## Task\n{blueprint.task}")
    sections.append(f"## Objective\n{blueprint.objective}")

    # --- Audience ---
    sections.append(f"## Audience\nThis output is intended for: {blueprint.audience}")

    # --- Examples (optional) ---
    if blueprint.examples:
        sections.append(f"## Examples\n{blueprint.examples}")

    # --- Style / Tone / Format ---
    format_label = _FORMAT_LABELS.get(blueprint.response_format, blueprint.response_format.value)
    style_parts = [
        f"Write in a **{blueprint.style.value}** style with a **{blueprint.tone.value}** tone.",
        f"Format your response as {format_label}.",
    ]
    if blueprint.length:
        style_parts.append(f"Target length: {blueprint.length}.")
    sections.append("## Style & Format\n" + "  ".join(style_parts))

    # --- Constraints (optional) ---
    if blueprint.constraints:
        sections.append(f"## Constraints\n{blueprint.constraints}")

    return "\n\n".join(sections)
