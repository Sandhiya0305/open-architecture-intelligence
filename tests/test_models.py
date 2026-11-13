from datetime import UTC, datetime

from oai_intelligence.config import load_yaml
from oai_intelligence.models import repository_observation
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
