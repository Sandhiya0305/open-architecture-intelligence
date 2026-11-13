from pathlib import Path

import pytest

from oai_intelligence.config import (
    ConfigError,
    load_yaml,
    validate_discovery,
    validate_sources,
)
from oai_intelligence.validation import validate_project_configs

ROOT = Path(__file__).resolve().parents[1]


def test_repository_configs_are_valid() -> None:
    validate_project_configs(ROOT)


def test_duplicate_source_ids_are_rejected() -> None:
    config = {
        "version": 1,
        "policy": {
            "respect_robots_txt": True,
            "respect_rate_limits": True,
            "store_source_urls": True,
            "republish_full_source_text": False,
        },
        "sources": [
            {"id": "same", "type": "api", "enabled": False},
            {"id": "same", "type": "api", "enabled": False},
        ],
    }
    with pytest.raises(ConfigError, match="duplicate source id"):
        validate_sources(config)


def test_yaml_root_must_be_a_mapping(tmp_path: Path) -> None:
    path = tmp_path / "invalid.yaml"
    path.write_text("- item\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="YAML mapping"):
        load_yaml(path)


def test_discovery_terms_must_not_be_empty() -> None:
    config = {
        "version": 1,
        "ecosystems": {
            "python": {"github_language": "Python", "query_terms": []}
        },
    }
    with pytest.raises(ConfigError, match="query_terms"):
        validate_discovery(config)
