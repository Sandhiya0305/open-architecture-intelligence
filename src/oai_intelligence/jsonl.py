"""Shared readers for append-only JSON Lines files."""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any


def iter_jsonl_objects(path: Path) -> Iterator[tuple[int, dict[str, Any]]]:
    """Yield object records with their one-based line numbers."""
    if not path.exists():
        return
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL in {path}:{line_number}: {exc}") from exc
            if not isinstance(value, dict):
                raise TypeError(f"Expected a JSON object in {path} at line {line_number}.")
            yield line_number, value


def read_jsonl_objects(path: Path) -> list[dict[str, Any]]:
    """Read all object records from a JSONL file."""
    return [record for _, record in iter_jsonl_objects(path)]
