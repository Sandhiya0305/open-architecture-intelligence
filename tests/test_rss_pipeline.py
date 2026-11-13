from datetime import UTC, datetime
from unittest.mock import patch

from oai_intelligence.config import load_yaml
from oai_intelligence.models import article_observation
from oai_intelligence.pipeline import run_rss_discovery
from oai_intelligence.validation import PROJECT_ROOT


def _article() -> dict:
    return {
        "feed_id": "sample-feed",
        "feed_title": "Sample Architecture Blog",
        "publisher": "Sample Architecture Blog",
        "entry_id": "https://example.com/clean",
        "title": "Clean Architecture in Python",
        "url": "https://example.com/clean",
        "summary": "A guide to clean architecture and dependency direction.",
        "author": "Sample Author",
        "published_at": "2026-11-12T12:00:00Z",
    }


def test_article_observation_is_unverified_and_cross_ecosystem() -> None:
    taxonomy = load_yaml(PROJECT_ROOT / "config" / "architecture_taxonomy.yaml")
    observation = article_observation(_article(), taxonomy, datetime(2026, 11, 13, tzinfo=UTC))
    assert observation["source"]["source_type"] == "article"
    assert observation["source"]["url"] == "https://example.com/clean"
    assert observation["ecosystem"] == "cross_ecosystem"
    assert "clean-architecture" in observation["architecture_matches"]
    assert observation["evidence_status"] == "unverified"
    assert observation["claim_type"] == "discovery_candidate"
    assert observation["metrics"] == {}


def test_rss_pipeline_deduplicates_feed_entries(tmp_path) -> None:
    article = _article()
    with patch(
        "oai_intelligence.pipeline.RSSCollector.fetch_feed",
        return_value=[article, article],
    ) as fetch:
        result = run_rss_discovery(limit=2, output_dir=tmp_path)

    assert fetch.call_count == 3
    assert result["articles_fetched"] == 6
    assert result["unique_articles"] == 1
    assert result["classified_candidates"] == 1
    assert result["new_observations"] == 1
    assert len(next(tmp_path.glob("*.jsonl")).read_text().splitlines()) == 1
