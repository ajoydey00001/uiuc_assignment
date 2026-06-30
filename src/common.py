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
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

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
    return None

