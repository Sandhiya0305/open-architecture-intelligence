import json
from datetime import date
from pathlib import Path

from oai_intelligence.claims import (
    build_review_queue,
    extract_claim_candidates,
    generate_claim_review_queue,
)


def observation(observation_id="obs-1", excerpt="The team chose microservices because independent deployment improved release speed."):
    return {
        "observation_id": observation_id,
        "source": {
            "source_id": "rss",
            "source_type": "article",
            "url": f"https://publisher.example/{observation_id}",
            "title": "Architecture case study",
            "content_excerpt": excerpt,
        },
        "architecture_matches": ["microservices"],
    }


def test_extracts_explicit_claim_sentence_with_source_provenance():
    claims = extract_claim_candidates(observation())

    assert len(claims) == 1
    assert "improved release speed" in claims[0]["claim_text"]
    assert claims[0]["source_url"] == "https://publisher.example/obs-1"
    assert claims[0]["evidence_status"] == "unverified"
    assert claims[0]["review_status"] == "pending"


def test_does_not_infer_claim_from_title_or_metadata_without_excerpt():
    item = observation(excerpt="")
    assert extract_claim_candidates(item) == []


def test_duplicate_claims_are_flagged_but_not_verified():
    sentence = "The team chose microservices because independent deployment improved release speed."
    queue = build_review_queue([observation("one", sentence), observation("two", sentence)])

    assert len(queue) == 2
    assert all(item["duplicate_observation_ids"] for item in queue)
    assert all(item["evidence_status"] == "unverified" for item in queue)


def test_review_queue_writes_json_jsonl_and_markdown(tmp_path: Path):
    data_dir = tmp_path / "observations"
    data_dir.mkdir()
    (data_dir / "2026-11-13.jsonl").write_text(
        json.dumps(observation()) + "\n", encoding="utf-8"
    )

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
