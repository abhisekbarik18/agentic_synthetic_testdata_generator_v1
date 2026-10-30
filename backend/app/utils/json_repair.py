"""
Resilient JSON extraction and repair utilities.
Handles markdown fences, trailing commas, truncated strings, unclosed braces/brackets,
and best-effort recovery from truncated LLM responses.
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.utils.logging_config import get_logger

logger = get_logger(__name__)


def extract_and_parse_json(text: str) -> Any:
    """
    Attempt to extract and parse JSON from text.
    Applies multi-stage recovery if initial parsing fails:
    1. Direct json.loads
    2. Strip markdown fences (```json ... ```)
    3. Extract outermost { ... } or [ ... ]
    4. Remove trailing commas
    5. Repair truncated strings and unclosed braces/brackets
    """
    if not text:
        raise ValueError("Empty input string")

    cleaned = text.strip()

    # Step 1: Strip markdown code blocks
    if "```" in cleaned:
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"```\s*$", "", cleaned, flags=re.MULTILINE).strip()

    # Step 2: Try direct parse
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Step 3: Extract outermost JSON structure
    first_brace = cleaned.find("{")
    first_bracket = cleaned.find("[")

    start_idx = -1
    is_object = True

    if first_brace != -1 and first_bracket != -1:
        if first_brace < first_bracket:
            start_idx = first_brace
            is_object = True
        else:
            start_idx = first_bracket
            is_object = False
    elif first_brace != -1:
        start_idx = first_brace
        is_object = True
    elif first_bracket != -1:
        start_idx = first_bracket
        is_object = False

    if start_idx != -1:
        end_char = "}" if is_object else "]"
        last_idx = cleaned.rfind(end_char)
        if last_idx > start_idx:
            candidate = cleaned[start_idx : last_idx + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass
        else:
            candidate = cleaned[start_idx:]
    else:
        candidate = cleaned

    # Step 4: Fix common syntax issues (trailing commas)
    candidate_no_trailing = re.sub(r",\s*([\]}])", r"\1", candidate)
    try:
        return json.loads(candidate_no_trailing)
    except json.JSONDecodeError:
        pass

    # Step 5: Repair truncated JSON (e.g. LLM ran out of max_tokens)
    repaired = _repair_truncated_json(candidate_no_trailing)
    try:
        logger.info("Successfully recovered JSON using truncation repair.")
        return json.loads(repaired)
    except json.JSONDecodeError as exc:
        logger.warning("Truncation repair failed: %s", exc)

    raise ValueError(f"Unable to parse JSON from text: {text[:200]}...")


def _repair_truncated_json(s: str) -> str:
    """
    Attempt to close open strings and balance unmatched brackets/braces
    caused by token-limit cutoffs.
    """
    s = s.strip()

    # Count quotes taking escapes into account
    in_string = False
    escaped = False
    stack: list[str] = []

    for char in s:
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if not in_string:
            if char in ("{", "["):
                stack.append(char)
            elif char == "}":
                if stack and stack[-1] == "{":
                    stack.pop()
            elif char == "]":
                if stack and stack[-1] == "[":
                    stack.pop()

    # If truncated inside a string literal, close it
    if in_string:
        s += '"'

    # Remove any trailing dangling comma, colon, or incomplete key
    s = re.sub(r",\s*$", "", s)
    s = re.sub(r":\s*$", ': ""', s)

    # Balance remaining open structures in reverse order
    while stack:
        open_char = stack.pop()
        if open_char == "{":
            # Strip trailing comma before closing
            s = re.sub(r",\s*$", "", s)
            s += "}"
        elif open_char == "[":
            s = re.sub(r",\s*$", "", s)
            s += "]"

    return s

