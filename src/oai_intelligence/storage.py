"""Append-only JSONL observation storage with idempotent daily writes."""

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from oai_intelligence.jsonl import iter_jsonl_objects


def append_observations(path: Path, observations: Sequence[Mapping[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing_ids: set[str] = set()
    if path.exists():
        for line_number, record in iter_jsonl_objects(path):
            observation_id = record.get("observation_id")
            if not isinstance(observation_id, str):
                raise TypeError(f"Invalid observation record in {path} at line {line_number}.")
            existing_ids.add(observation_id)

    added = 0
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        for observation in observations:
            observation_id = observation["observation_id"]
            if observation_id in existing_ids:
                continue
            stream.write(json.dumps(dict(observation), ensure_ascii=False, sort_keys=True) + "\n")
            existing_ids.add(observation_id)
            added += 1
        stream.flush()
    return added
