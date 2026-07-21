from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def read_prompt_metadata(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_prompt_text(prompt_set_path: Path, prompt_id: str) -> str:
    text = prompt_set_path.read_text(encoding="utf-8")
    pattern = rf"## {re.escape(prompt_id)}\n\n(.*?)(?=\n## |\Z)"
    match = re.search(pattern, text, flags=re.S)
    if not match:
        raise ValueError(f"Could not find prompt {prompt_id} in {prompt_set_path}")
    return match.group(1).strip()


def safe_model_name(model: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", model).strip("_")


def load_json_lenient(text: str) -> Any | None:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    # Small models sometimes emit Python literals (None/True/False) instead of JSON
    # ones, which invalidates the whole document. Try the text as-is first, then a
    # normalized copy. (Word-boundary substitution can in principle touch a literal
    # None inside a string value; acceptable for a lenient best-effort parser.)
    normalized = re.sub(r"\bNone\b", "null", cleaned)
    normalized = re.sub(r"\bTrue\b", "true", normalized)
    normalized = re.sub(r"\bFalse\b", "false", normalized)
    candidates = [cleaned, normalized] if normalized != cleaned else [cleaned]

    # All direct parses must be tried before any salvage attempt: salvage returns a
    # *partial* result, and letting it run on the raw text first would mask a clean
    # full parse of the normalized text.
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    for candidate in candidates:
        result = _salvage_json(candidate)
        if result is not None:
            return result
    return None


def _salvage_json(cleaned: str) -> Any | None:
    start_positions = [i for i in [cleaned.find("{"), cleaned.find("[")] if i >= 0]
    if not start_positions:
        return None
    start = min(start_positions)
    for end in range(len(cleaned), start, -1):
        candidate = cleaned[start:end].strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    # Trailing-garbage trimming above cannot recover JSON truncated mid-stream (e.g.
    # a response cut off at max_tokens never closes its brackets, so no substring
    # parses). Repair attempt: cut back to a structural boundary (after a '}' / ']'
    # or before a ','), close any still-open brackets, and try again -- recovering
    # every complete item and losing only the final partial one.
    fragment = cleaned[start:]
    cut_points = [m.start() for m in re.finditer(r"[}\],]", fragment)]
    for pos in reversed(cut_points[-300:]):
        prefix = fragment[: pos + 1]
        if prefix.rstrip().endswith(","):
            prefix = prefix.rstrip()[:-1]
        repaired = _close_open_brackets(prefix)
        if repaired is None:
            continue
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            continue
    return None


def _close_open_brackets(fragment: str) -> str | None:
    """Append the closers for any unclosed {/[ in fragment, tracking string state so
    brackets inside string values are ignored. Returns None if fragment ends inside a
    string or closes a bracket it never opened (unrepairable cut point)."""
    stack: list[str] = []
    in_string = False
    escape = False
    for ch in fragment:
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch in "{[":
                stack.append(ch)
            elif ch in "}]":
                if not stack:
                    return None
                stack.pop()
    if in_string:
        return None
    return fragment + "".join("}" if ch == "{" else "]" for ch in reversed(stack))

