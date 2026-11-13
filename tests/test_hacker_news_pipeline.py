from datetime import UTC, datetime
from unittest.mock import patch

from oai_intelligence.config import load_yaml
from oai_intelligence.models import discussion_observation
from oai_intelligence.pipeline import run_hacker_news_discovery
from oai_intelligence.validation import PROJECT_ROOT


def _story() -> dict:
    return {
        "objectID": "98765",
        "title": "Show HN: Clean Architecture in Python",
        "story_text": "A practical clean architecture example.",
        "url": "https://example.com/clean-architecture",
        "created_at": "2026-11-12T12:00:00Z",
        "points": 42,
        "num_comments": 12,
        "author": "sample-user",
    }


def test_discussion_observation_is_cross_ecosystem_and_unverified() -> None:
    taxonomy = load_yaml(PROJECT_ROOT / "config" / "architecture_taxonomy.yaml")
    observation = discussion_observation(
        _story(), taxonomy, datetime(2026, 11, 13, tzinfo=UTC)
    )
    assert observation["source"]["source_type"] == "discussion"
    assert observation["source"]["url"].endswith("id=98765")
    assert observation["ecosystem"] == "cross_ecosystem"
    assert "clean-architecture" in observation["architecture_matches"]
    assert observation["evidence_status"] == "unverified"
    assert observation["metrics"]["points"] == 42
    assert observation["metrics"]["story_url"] == "https://example.com/clean-architecture"


def test_hacker_news_pipeline_deduplicates_results(tmp_path) -> None:
    story = _story()
    with patch(
        "oai_intelligence.pipeline.HackerNewsCollector.search_stories",
        return_value=[story, story],
    ) as search:
        result = run_hacker_news_discovery(
            limit=2, output_dir=tmp_path, dry_run=False
        )
    assert search.call_count == 5
    assert result["unique_stories"] == 1
    assert result["classified_candidates"] == 1
    assert result["new_observations"] == 1
    assert len(next(tmp_path.glob("*.jsonl")).read_text().splitlines()) == 1
