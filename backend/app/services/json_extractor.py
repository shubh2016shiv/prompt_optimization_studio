"""
LLM JSON extraction helpers.

Purpose:
  Parse JSON payloads from LLM responses that may include markdown fences or
  extra commentary. This keeps downstream parsing resilient without changing
  the model prompts.

Behavior:
  Attempts direct JSON parsing, then code-fence extraction, then heuristic
  object/array scanning. Raises a dedicated JSONExtractionError on failure.
"""

import json
import re
from typing import Any


class JSONExtractionError(Exception):
    """Raised when JSON cannot be extracted from the LLM response."""

    pass


def extract_json_from_llm_response(response_text: str) -> dict[str, Any]:
    """
    Extract JSON from an LLM response that may be wrapped in markdown fences.

    Args:
        response_text: The raw text response from the LLM.

    Returns:
        The parsed JSON as a dictionary.

    Raises:
        JSONExtractionError: If JSON cannot be extracted or parsed.
    """
    if not response_text or not response_text.strip():
        raise JSONExtractionError("Empty response from LLM")

    text = response_text.strip()

    # Try to parse directly first (ideal case)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Remove markdown code fences with optional language specifier
    # Handles: ```json\n{...}\n``` and ```\n{...}\n```
    code_fence_pattern = r"```(?:json)?\s*\n?([\s\S]*?)\n?```"
    matches = re.findall(code_fence_pattern, text, re.IGNORECASE)

    if matches:
        # Try the first match
        try:
            return json.loads(matches[0].strip())
        except json.JSONDecodeError:
            pass

        # Try all matches in case the first one isn't valid JSON
        for match in matches[1:]:
            try:
                return json.loads(match.strip())
            except json.JSONDecodeError:
                continue

    # Try to find JSON object/array boundaries
    json_object_pattern = r"\{[\s\S]*\}"
    json_array_pattern = r"\[[\s\S]*\]"

    # Try object pattern first (most common for our use case)
    object_match = re.search(json_object_pattern, text)
    if object_match:
        try:
            return json.loads(object_match.group())
        except json.JSONDecodeError:
            pass

    # Try array pattern
    array_match = re.search(json_array_pattern, text)
    if array_match:
        try:
            return json.loads(array_match.group())
        except json.JSONDecodeError:
            pass

    # Last resort: try to clean up common issues
    cleaned = text
    # Remove leading/trailing non-JSON content
    cleaned = re.sub(r"^[^{\[]*", "", cleaned)
    cleaned = re.sub(r"[^}\]]*$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise JSONExtractionError(
            f"Failed to extract valid JSON from LLM response: {str(e)}\n"
            f"Response preview: {text[:500]}..."
        )
