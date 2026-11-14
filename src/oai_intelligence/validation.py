"""Deterministic validation for configuration and observation records."""

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from oai_intelligence.config import load_yaml, validate_discovery, validate_sources

_PACKAGE_ROOT = Path(__file__).resolve().parent
_CHECKOUT_ROOT = _PACKAGE_ROOT.parents[1]
_IN_CHECKOUT = (_CHECKOUT_ROOT / "config").is_dir() and (_CHECKOUT_ROOT / "schema").is_dir()

# Configurations and schemas travel with the wheel; mutable data stays outside site-packages.
CONFIG_ROOT = _CHECKOUT_ROOT if _IN_CHECKOUT else _PACKAGE_ROOT / "resources"
PROJECT_ROOT = (
    _CHECKOUT_ROOT
    if _IN_CHECKOUT
    else Path(os.environ.get("OAI_HOME", Path.cwd())).expanduser().resolve()
)
SCHEMA_PATH = CONFIG_ROOT / "schema" / "observation.schema.json"
CLAIM_SCHEMA_PATH = CONFIG_ROOT / "schema" / "claim.schema.json"
REVIEW_SCHEMA_PATH = CONFIG_ROOT / "schema" / "review-decision.schema.json"


@lru_cache(maxsize=8)
def _schema_validator(schema_path: Path) -> Draft202012Validator:
    with schema_path.open(encoding="utf-8") as stream:
        schema = json.load(stream)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _config_root(root: Path | None) -> Path:
    if root is not None and (root / "config").is_dir() and (root / "schema").is_dir():
        return root
    return CONFIG_ROOT


def validate_project_configs(root: Path | None = None) -> None:
    """Validate checkout configuration or the immutable resources bundled in the wheel."""
    config_root = _config_root(root)
    for schema_name in (
        "observation.schema.json",
        "claim.schema.json",
        "review-decision.schema.json",
    ):
        _schema_validator((config_root / "schema" / schema_name).resolve())
    validate_sources(load_yaml(config_root / "config" / "sources.yaml"))
    validate_discovery(load_yaml(config_root / "config" / "discovery.yaml"))
    taxonomy = load_yaml(config_root / "config" / "architecture_taxonomy.yaml")
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
    _schema_validator(schema_path.resolve()).validate(observation)


def validate_claim(claim: dict[str, Any], schema_path: Path = CLAIM_SCHEMA_PATH) -> None:
    """Validate a source-linked candidate claim against its versioned contract."""
    _schema_validator(schema_path.resolve()).validate(claim)


def validate_review_decision(
    decision: dict[str, Any], schema_path: Path = REVIEW_SCHEMA_PATH
) -> None:
    """Validate an append-only human review decision."""
    _schema_validator(schema_path.resolve()).validate(decision)
