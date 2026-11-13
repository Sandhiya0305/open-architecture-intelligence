"""Deterministic validation for configuration and observation records."""

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from oai_intelligence.config import load_yaml, validate_discovery, validate_sources

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = PROJECT_ROOT / "schema" / "observation.schema.json"
CLAIM_SCHEMA_PATH = PROJECT_ROOT / "schema" / "claim.schema.json"
REVIEW_SCHEMA_PATH = PROJECT_ROOT / "schema" / "review-decision.schema.json"


def validate_project_configs(root: Path = PROJECT_ROOT) -> None:
    for schema_name in ("observation.schema.json", "claim.schema.json", "review-decision.schema.json"):
        schema_path = root / "schema" / schema_name
        with schema_path.open(encoding="utf-8") as stream:
            Draft202012Validator.check_schema(json.load(stream))
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


def _validate_with_schema(record: dict[str, Any], schema_path: Path) -> None:
    with schema_path.open(encoding="utf-8") as stream:
        schema = json.load(stream)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(record)


def validate_claim(claim: dict[str, Any], schema_path: Path = CLAIM_SCHEMA_PATH) -> None:
    """Validate a source-linked candidate claim against its versioned contract."""
    _validate_with_schema(claim, schema_path)


def validate_review_decision(
    decision: dict[str, Any], schema_path: Path = REVIEW_SCHEMA_PATH
) -> None:
    """Validate an append-only human review decision."""
    _validate_with_schema(decision, schema_path)
