"""Deterministic validation for configuration and observation records."""

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from oai_intelligence.config import load_yaml, validate_discovery, validate_sources

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = PROJECT_ROOT / "schema" / "observation.schema.json"


def validate_project_configs(root: Path = PROJECT_ROOT) -> None:
    validate_sources(load_yaml(root / "config" / "sources.yaml"))
    validate_discovery(load_yaml(root / "config" / "discovery.yaml"))
    taxonomy = load_yaml(root / "config" / "architecture_taxonomy.yaml")
    if taxonomy.get("version") != 1:
        raise ValueError("architecture_taxonomy.yaml: version must be 1.")
    architectures = taxonomy.get("architectures")
    if not isinstance(architectures, list) or not architectures:
        raise ValueError("architecture_taxonomy.yaml: architectures must be a non-empty list.")
    ids: set[str] = set()
    for item in architectures:
        if not isinstance(item, dict) or not all(
            item.get(key) for key in ("id", "name", "description")
        ):
            raise ValueError("Each architecture needs id, name, and description.")
        if item["id"] in ids:
            raise ValueError(f"Duplicate architecture id: {item['id']}")
        ids.add(item["id"])
        if not isinstance(item.get("aliases", []), list):
            raise TypeError(f"Aliases for {item['id']} must be a list.")


def validate_observation(
    observation: dict[str, Any], schema_path: Path = SCHEMA_PATH
) -> None:
    with schema_path.open(encoding="utf-8") as stream:
        schema = json.load(stream)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(observation)
