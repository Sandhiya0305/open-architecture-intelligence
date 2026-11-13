import json
from datetime import date
from pathlib import Path

import pytest

from oai_intelligence.review import prepare_knowledge_candidates, record_claim_review

AS_OF = date(2026, 11, 13)
CLAIM_ID = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


def setup_queue(tmp_path: Path) -> tuple[Path, Path]:
    queue_dir = tmp_path / "queue"
    queue_dir.mkdir()
    (queue_dir / f"{AS_OF.isoformat()}.json").write_text(
        json.dumps([{
            "claim_id": CLAIM_ID,
            "claim_text": "Independent deployment improved release speed.",
            "architecture_ids": ["microservices"],
            "claim_kinds": ["benefit"],
            "source_title": "A case study",
            "source_url": "https://example.org/case-study",
            "observation_id": "observation-1",
        }]),
        encoding="utf-8",
    )
    return queue_dir, tmp_path / "reviews" / "decisions.jsonl"


def test_review_decision_is_appended_with_reviewer_and_note(tmp_path: Path):
    queue_dir, reviews_file = setup_queue(tmp_path)
    result = record_claim_review(
        CLAIM_ID, "approve", "reviewer@example.org", "Source context checked.",
        queue_dir, reviews_file, AS_OF,
    )

    saved = json.loads(reviews_file.read_text(encoding="utf-8").strip())
    assert saved == result
    assert saved["decision"] == "approve"
    assert saved["reviewer"] == "reviewer@example.org"


def test_unknown_claim_cannot_be_reviewed(tmp_path: Path):
    queue_dir, reviews_file = setup_queue(tmp_path)
    with pytest.raises(ValueError, match="not present"):
        record_claim_review("unknown", "approve", "reviewer", "Checked", queue_dir, reviews_file, AS_OF)


def test_knowledge_bundle_includes_only_human_approved_claims_and_keeps_unverified_label(tmp_path: Path):
    queue_dir, reviews_file = setup_queue(tmp_path)
    record_claim_review(CLAIM_ID, "approve", "reviewer", "Relevant source.", queue_dir, reviews_file, AS_OF)
    result = prepare_knowledge_candidates(
        queue_dir=queue_dir, reviews_file=reviews_file,
        output_dir=tmp_path / "output", as_of=AS_OF,
    )

    content = Path(result["output"]).read_text(encoding="utf-8")
    assert result["approved_candidates"] == 1
    assert "Evidence status: **UNVERIFIED**" in content
    assert "https://example.org/case-study" in content
    assert "reviewer" in content


def test_no_approved_claims_produces_empty_candidate_bundle(tmp_path: Path):
    queue_dir, reviews_file = setup_queue(tmp_path)
    record_claim_review(CLAIM_ID, "needs-evidence", "reviewer", "Need methodology.", queue_dir, reviews_file, AS_OF)
    result = prepare_knowledge_candidates(
        queue_dir=queue_dir, reviews_file=reviews_file,
        output_dir=tmp_path / "output", as_of=AS_OF,
    )
    assert result["approved_candidates"] == 0
    assert "No claims have been approved" in Path(result["output"]).read_text(encoding="utf-8")


def test_later_review_decision_supersedes_earlier_decision(tmp_path: Path):
    queue_dir, reviews_file = setup_queue(tmp_path)
    record_claim_review(CLAIM_ID, "approve", "reviewer", "Initially approved.", queue_dir, reviews_file, AS_OF)
    record_claim_review(CLAIM_ID, "reject", "reviewer", "New source context invalidates it.", queue_dir, reviews_file, AS_OF)
    result = prepare_knowledge_candidates(
        queue_dir=queue_dir, reviews_file=reviews_file,
        output_dir=tmp_path / "output", as_of=AS_OF,
    )
    assert result["approved_candidates"] == 0
    assert len(reviews_file.read_text(encoding="utf-8").splitlines()) == 2


def test_regenerated_claim_queue_reflects_latest_human_decision(tmp_path: Path):
    from oai_intelligence.claims import generate_claim_review_queue

    data_dir = tmp_path / "observations"
    data_dir.mkdir()
    source_observation = {
        "observation_id": "observation-live",
        "architecture_matches": ["microservices"],
        "source": {
            "source_id": "rss",
            "url": "https://example.org/article",
            "title": "Architecture report",
            "content_excerpt": "The team chose microservices because independent deployment improved release speed.",
        },
    }
    (data_dir / f"{AS_OF.isoformat()}.jsonl").write_text(
        json.dumps(source_observation) + "\n", encoding="utf-8"
    )
    queue_dir = tmp_path / "queue"
    reviews_file = tmp_path / "reviews.jsonl"
    result = generate_claim_review_queue(data_dir, queue_dir, AS_OF, reviews_file)
    claim = json.loads(Path(result["json"]).read_text(encoding="utf-8"))[0]
    record_claim_review(
        claim["claim_id"], "approve", "reviewer", "Source and context checked.",
        queue_dir, reviews_file, AS_OF,
    )
    refreshed = generate_claim_review_queue(data_dir, queue_dir, AS_OF, reviews_file)
    refreshed_claim = json.loads(Path(refreshed["json"]).read_text(encoding="utf-8"))[0]

    assert refreshed_claim["review_status"] == "approve"
    assert refreshed_claim["reviewer"] == "reviewer"

