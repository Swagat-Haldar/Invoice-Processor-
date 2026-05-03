from __future__ import annotations

import json
import re
from typing import Any


_JSON_OBJ_RE = re.compile(r"\{.*\}", re.DOTALL)


def extract_json_object(text: str) -> str | None:
    """
    Extract the first top-level JSON object from a model response.

    Gemini sometimes wraps JSON in markdown or adds explanation text; we strip that.
    """
    if not text:
        return None

    # Fast path: strip code fences first.
    cleaned = re.sub(r"^```(?:json)?\s*|```$", "", text.strip(), flags=re.IGNORECASE | re.MULTILINE)

    # Find first "{" ... last "}" block.
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        # Try regex fallback.
        m = _JSON_OBJ_RE.search(cleaned)
        if not m:
            return None
        return m.group(0)
    return cleaned[start : end + 1]


def safe_json_loads(text: str) -> tuple[Any | None, str | None]:
    """
    Returns (parsed_object, error_message).
    """
    json_str = extract_json_object(text)
    if not json_str:
        return None, "No JSON object found in Gemini response."

    try:
        return json.loads(json_str), None
    except json.JSONDecodeError as e:
        return None, f"JSON decode error: {e.msg}"

