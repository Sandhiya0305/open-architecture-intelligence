"""Append-only JSONL observation storage with idempotent daily writes."""

import json
from pathlib import Path
from typing import Any


def append_observations(path: Path, observations: list[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing_ids: set[str] = set()
    if path.exists():
        with path.open(encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, start=1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Invalid JSONL in {path} at line {line_number}: {exc}"
                    ) from exc
                if not isinstance(record, dict) or not isinstance(
                    record.get("observation_id"), str
                ):
                    raise TypeError(
                        f"Invalid observation record in {path} at line {line_number}."
                    )
                existing_ids.add(record["observation_id"])

    added = 0
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        for observation in observations:
            observation_id = observation["observation_id"]
            if observation_id in existing_ids:
                continue
            stream.write(json.dumps(observation, ensure_ascii=False, sort_keys=True) + "\n")
            existing_ids.add(observation_id)
            added += 1
        stream.flush()
    return added
