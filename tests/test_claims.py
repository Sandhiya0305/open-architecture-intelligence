import json
from datetime import date
from pathlib import Path

from oai_intelligence.claims import (
    build_review_queue,
    extract_claim_candidates,
    generate_claim_review_queue,
)

CLAIM_SENTENCE = (
    "The microservices architecture improved independent deployment speed "
    "across product teams by reducing release coordination."
)


def observation(
    observation_id="obs-1",
    excerpt=CLAIM_SENTENCE,
    source_id="rss",
    source_type="article",
):
    return {
        "schema_version": 1,
        "observation_id": observation_id,
        "source_record_id": f"rss:feed:{observation_id}",
        "source": {
            "source_id": source_id,
            "source_type": source_type,
            "url": f"https://publisher.example/{observation_id}",
            "title": "Architecture case study",
            "publisher": "Example Engineering",
            "publisher_type": "editorial",
            "content_excerpt": excerpt,
            "published_at": None,
            "retrieved_at": "2026-11-13T00:00:00Z",
        },
        "observed_at": "2026-11-13T00:00:00Z",
        "category": "microservices",
        "architecture_matches": ["microservices"],
        "ecosystem": "cross_ecosystem",
        "claim": "Discovery metadata only.",
        "claim_type": "discovery_candidate",
        "evidence_status": "unverified",
        "evidence_notes": "Needs review.",
        "tags": [],
        "metrics": {},
    }


def test_extracts_architecture_specific_sentence_with_source_provenance():
    claims = extract_claim_candidates(observation())

    assert len(claims) == 1
    assert "microservices architecture" in claims[0]["claim_text"]
    assert claims[0]["source_url"] == "https://publisher.example/obs-1"
    assert claims[0]["evidence_status"] == "unverified"
    assert claims[0]["review_status"] == "pending"
    assert claims[0]["schema_version"] == 1


def test_excludes_repository_descriptions_and_discussion_posts():
    sentence = CLAIM_SENTENCE
    assert (
        extract_claim_candidates(
            observation(source_id="github", source_type="repository", excerpt=sentence)
        )
        == []
    )
    assert (
        extract_claim_candidates(
            observation(source_id="hacker_news", source_type="discussion", excerpt=sentence)
        )
        == []
    )


def test_does_not_infer_claim_from_metadata_or_non_architecture_sentence():
    assert (
        extract_claim_candidates(
            observation(excerpt="The team improved release speed across product teams.")
        )
        == []
    )


def test_strips_html_and_entities_before_extraction():
    item = observation(
        excerpt=(
            "<p>The microservices architecture improved independent deployment speed "
            "by reducing coordination across product teams&#x27; services.</p>"
        )
    )
    claims = extract_claim_candidates(item)
    assert len(claims) == 1
    assert "<p>" not in claims[0]["claim_text"]
    assert "&#x27;" not in claims[0]["claim_text"]
    assert "teams' services" in claims[0]["claim_text"]


def test_rejects_truncated_sentence():
    item = observation(excerpt=CLAIM_SENTENCE[:-1] + "...")
    assert extract_claim_candidates(item) == []


def test_repeated_observations_from_same_source_are_collapsed():
    sentence = CLAIM_SENTENCE
    first = observation("day-one", sentence)
    second = observation("day-two", sentence)
    second["source_record_id"] = first["source_record_id"]
    second["source"]["url"] = first["source"]["url"]
    queue = build_review_queue([first, second])

    assert len(queue) == 1
    assert queue[0]["claim_id"] == extract_claim_candidates(first)[0]["claim_id"]
    assert queue[0]["duplicate_observation_ids"] == []


def test_same_claim_from_different_sources_is_flagged_for_independence_review():
    sentence = CLAIM_SENTENCE
    first = observation("one", sentence)
    second = observation("two", sentence)
    queue = build_review_queue([first, second])

    assert len(queue) == 2
    assert all(item["duplicate_observation_ids"] for item in queue)
    assert queue[0]["claim_id"] != queue[1]["claim_id"]
    assert all(item["evidence_status"] == "unverified" for item in queue)


def test_review_queue_writes_json_jsonl_and_markdown(tmp_path: Path):
    data_dir = tmp_path / "observations"
    data_dir.mkdir()
    (data_dir / "2026-11-13.jsonl").write_text(json.dumps(observation()) + "\n", encoding="utf-8")

    result = generate_claim_review_queue(
        data_dir=data_dir,
        output_dir=tmp_path / "claims",
        as_of=date(2026, 11, 13),
    )

    assert result["observations_scanned"] == 1
    assert result["claims_extracted"] == 1
    assert Path(result["json"]).exists()
    assert Path(result["jsonl"]).exists()
    assert "unverified" in Path(result["markdown"]).read_text(encoding="utf-8")


def test_daily_queue_contains_only_first_seen_claims_for_that_date(tmp_path: Path):
    data_dir = tmp_path / "observations"
    data_dir.mkdir()
    first = observation("day-one")
    first["observed_at"] = "2026-11-13T00:00:00Z"
    second = observation("day-two", source_id="rss")
    second["source_record_id"] = "rss:feed:new-article"
    second["source"]["url"] = "https://publisher.example/new-article"
    second["observed_at"] = "2026-11-14T00:00:00Z"
    (data_dir / "2026-11-13.jsonl").write_text(json.dumps(first) + "\n", encoding="utf-8")
    (data_dir / "2026-11-14.jsonl").write_text(json.dumps(second) + "\n", encoding="utf-8")

    result = generate_claim_review_queue(
        data_dir=data_dir,
        output_dir=tmp_path / "claims",
        as_of=date(2026, 11, 14),
    )
    queue = json.loads(Path(result["json"]).read_text(encoding="utf-8"))

    assert result["observations_scanned"] == 2
    assert result["claims_extracted"] == 1
    assert queue[0]["source_record_id"] == "rss:feed:new-article"


def test_vendor_marketing_source_is_not_promoted_to_claim_queue():
    item = observation()
    item["source"]["publisher"] = "Vendor Engineering Blog"
    item["source"]["publisher_type"] = "vendor"

    assert extract_claim_candidates(item) == []


def test_rejects_promotional_scalability_statement_without_context():
    item = observation(
        excerpt="Our microservices architecture is scalable to millions of executions."
    )

    assert extract_claim_candidates(item) == []
