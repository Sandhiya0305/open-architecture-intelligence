from datetime import UTC, datetime

from oai_intelligence.config import load_yaml
from oai_intelligence.models import (
    article_observation,
    classify_architectures,
    repository_observation,
)
from oai_intelligence.validation import PROJECT_ROOT


def test_repository_is_classified_and_validated() -> None:
    taxonomy = load_yaml(PROJECT_ROOT / "config" / "architecture_taxonomy.yaml")
    repository = {
        "name": "clean-architecture-python",
        "full_name": "sample/clean-architecture-python",
        "description": "A clean architecture example with explicit source context.",
        "topics": ["clean-architecture"],
        "html_url": "https://github.com/sample/clean-architecture-python",
        "stargazers_count": 12,
        "forks_count": 3,
        "open_issues_count": 1,
        "language": "Python",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2026-11-12T00:00:00Z",
        "pushed_at": "2026-11-12T00:00:00Z",
        "default_branch": "main",
        "archived": False,
        "license": {"spdx_id": "MIT"},
    }
    observation = repository_observation(
        repository, "python", taxonomy, datetime(2026, 11, 13, tzinfo=UTC)
    )
    assert observation["schema_version"] == 1
    assert observation["category"] == "clean-architecture"
    assert observation["evidence_status"] == "unverified"
    assert observation["claim_type"] == "discovery_candidate"
    assert observation["metrics"]["stars"] == 12
    assert observation["metrics"]["license_spdx_id"] == "MIT"
    assert observation["source"]["content_excerpt"] == repository["description"]


def test_same_repository_same_day_has_stable_observation_id() -> None:
    taxonomy = load_yaml(PROJECT_ROOT / "config" / "architecture_taxonomy.yaml")
    repository = {
        "name": "microservices",
        "full_name": "sample/microservices",
        "description": "microservices",
        "topics": [],
        "html_url": "https://github.com/sample/microservices",
        "stargazers_count": 0,
        "forks_count": 0,
        "open_issues_count": 0,
        "language": "Python",
        "created_at": None,
        "updated_at": None,
        "pushed_at": None,
        "default_branch": "main",
        "archived": False,
        "license": None,
    }
    now = datetime(2026, 11, 13, 10, tzinfo=UTC)
    first = repository_observation(repository, "python", taxonomy, now)
    second = repository_observation(repository, "python", taxonomy, now)
    assert first["observation_id"] == second["observation_id"]


def test_classifier_does_not_match_bare_taxonomy_id():
    taxonomy = load_yaml(PROJECT_ROOT / "config" / "architecture_taxonomy.yaml")
    assert classify_architectures({"name": "layered"}, taxonomy) == []
    assert classify_architectures({"name": "Layered Architecture example"}, taxonomy) == ["layered"]


def test_classifier_uses_explicit_aliases():
    taxonomy = load_yaml(PROJECT_ROOT / "config" / "architecture_taxonomy.yaml")
    assert classify_architectures({"name": "Ports and Adapters example"}, taxonomy) == [
        "clean-architecture"
    ]


def test_article_performance_language_is_flagged_for_methodology_review():
    taxonomy = load_yaml(PROJECT_ROOT / "config" / "architecture_taxonomy.yaml")
    article = {
        "url": "https://example.org/benchmark",
        "title": "Microservices benchmark",
        "feed_id": "infoq_architecture",
        "publisher": "InfoQ Architecture & Design",
        "publisher_type": "editorial",
        "summary": "A benchmark measured p95 latency at 42 ms under the documented workload.",
    }

    observation = article_observation(article, taxonomy, datetime(2026, 11, 14, tzinfo=UTC))

    assert observation["claim_type"] == "performance_claim"
    assert observation["evidence_status"] == "unverified"
