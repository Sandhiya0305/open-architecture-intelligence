"""Load and validate the project's YAML configuration files."""

from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    """Raised when a project configuration is missing or invalid."""


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as stream:
            data = yaml.safe_load(stream)
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError(f"Cannot load {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"{path} must contain a YAML mapping.")
    return data


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ConfigError(message)


def validate_sources(data: dict[str, Any]) -> None:
    _require(data.get("version") == 1, "sources.yaml: version must be 1.")
    policy = data.get("policy")
    _require(isinstance(policy, dict), "sources.yaml: policy must be a mapping.")
    for key in ("respect_robots_txt", "respect_rate_limits", "store_source_urls"):
        _require(policy.get(key) is True, f"sources.yaml: policy.{key} must be true.")
    _require(
        policy.get("republish_full_source_text") is False,
        "sources.yaml: full source text republishing must be disabled.",
    )
    sources = data.get("sources")
    _require(
        isinstance(sources, list) and bool(sources),
        "sources.yaml: sources must be a non-empty list.",
    )
    ids: set[str] = set()
    for source in sources:
        _require(isinstance(source, dict), "sources.yaml: each source must be a mapping.")
        source_id = source.get("id")
        _require(
            isinstance(source_id, str) and bool(source_id.strip()),
            "sources.yaml: every source needs a non-empty id.",
        )
        _require(source_id not in ids, f"sources.yaml: duplicate source id {source_id!r}.")
        ids.add(source_id)
        _require(
            isinstance(source.get("enabled"), bool),
            f"sources.yaml: {source_id} needs an enabled boolean.",
        )
        _require(
            source.get("type") in {"api", "feed"},
            f"sources.yaml: {source_id} has an unsupported type.",
        )
        if source.get("enabled"):
            _require(
                bool(source.get("endpoint") or source.get("feeds")),
                f"sources.yaml: enabled source {source_id} needs endpoint or feeds.",
            )


def validate_discovery(data: dict[str, Any]) -> None:
    _require(data.get("version") == 1, "discovery.yaml: version must be 1.")
    ecosystems = data.get("ecosystems")
    _require(
        isinstance(ecosystems, dict) and bool(ecosystems),
        "discovery.yaml: ecosystems must be a non-empty mapping.",
    )
    for ecosystem, settings in ecosystems.items():
        _require(isinstance(settings, dict), f"{ecosystem}: settings must be a mapping.")
        _require(
            isinstance(settings.get("github_language"), str)
            and bool(settings["github_language"].strip()),
            f"{ecosystem}: github_language is required.",
        )
        terms = settings.get("query_terms")
        _require(
            isinstance(terms, list)
            and bool(terms)
            and all(isinstance(term, str) and term.strip() for term in terms),
            f"{ecosystem}: query_terms must be a non-empty list of strings.",
        )
