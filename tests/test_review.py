import json
from datetime import date
from pathlib import Path

import pytest

from oai_intelligence import review
from oai_intelligence.review import (
    ReviewAuthenticationError,
    prepare_knowledge_candidates,
    record_claim_review,
)

AS_OF = date(2026, 11, 13)
CLAIM_ID = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


@pytest.fixture(autouse=True)
def authenticated_reviewer(monkeypatch):
    monkeypatch.setenv("OAI_REVIEW_TOKEN", "test-token")
    monkeypatch.setattr(
        review,
        "_authenticated_github_user",
        lambda token: {"login": "reviewer", "id": 123456},
    )


def setup_queue(tmp_path: Path) -> tuple[Path, Path]:
    queue_dir = tmp_path / "queue"
    queue_dir.mkdir()
    (queue_dir / f"{AS_OF.isoformat()}.json").write_text(
        json.dumps(
            [
                {
                    "claim_id": CLAIM_ID,
                    "claim_text": "Independent deployment improved release speed.",
                    "architecture_ids": ["microservices"],
                    "claim_kinds": ["benefit"],
                    "source_title": "A case study",
                    "source_url": "https://example.org/case-study",
                    "observation_id": "observation-1",
                }
            ]
        ),
        encoding="utf-8",
    )
    return queue_dir, tmp_path / "reviews" / "decisions.jsonl"


def test_review_decision_is_authenticated_and_records_source_attestation(tmp_path: Path):
    queue_dir, reviews_file = setup_queue(tmp_path)
    result = record_claim_review(
        CLAIM_ID,
        "approve",
        "reviewer",
        "Source and context checked.",
        queue_dir,
        reviews_file,
        AS_OF,
        source_checked=True,
    )

    saved = json.loads(reviews_file.read_text(encoding="utf-8").strip())
    assert saved == result
    assert saved["schema_version"] == 1
    assert saved["decision"] == "approve"
    assert saved["reviewer"] == "reviewer"
    assert saved["reviewer_id"] == 123456
    assert saved["source_checked"] is True
    assert saved["reviewed_source_url"] == "https://example.org/case-study"


def test_missing_review_token_is_rejected(tmp_path: Path, monkeypatch):
    queue_dir, reviews_file = setup_queue(tmp_path)
    monkeypatch.delenv("OAI_REVIEW_TOKEN")
    with pytest.raises(ReviewAuthenticationError, match="OAI_REVIEW_TOKEN"):
        record_claim_review(
            CLAIM_ID,
            "approve",
            "reviewer",
            "Checked.",
            queue_dir,
            reviews_file,
            AS_OF,
            source_checked=True,
        )


def test_reviewer_must_match_authenticated_github_account(tmp_path: Path):
    queue_dir, reviews_file = setup_queue(tmp_path)
    with pytest.raises(ReviewAuthenticationError, match="must match"):
        record_claim_review(
            CLAIM_ID,
            "approve",
            "not-the-reviewer",
            "Checked.",
            queue_dir,
            reviews_file,
            AS_OF,
            source_checked=True,
        )


def test_source_check_attestation_is_required(tmp_path: Path):
    queue_dir, reviews_file = setup_queue(tmp_path)
    with pytest.raises(ValueError, match="--source-checked"):
        record_claim_review(
            CLAIM_ID, "approve", "reviewer", "Checked.", queue_dir, reviews_file, AS_OF
        )


def test_unknown_claim_cannot_be_reviewed(tmp_path: Path):
    queue_dir, reviews_file = setup_queue(tmp_path)
    with pytest.raises(ValueError, match="not present"):
        record_claim_review(
            "unknown",
            "approve",
            "reviewer",
            "Checked.",
            queue_dir,
            reviews_file,
            AS_OF,
            source_checked=True,
        )


def test_knowledge_bundle_includes_only_authenticated_approvals(tmp_path: Path):
    queue_dir, reviews_file = setup_queue(tmp_path)
    record_claim_review(
        CLAIM_ID,
        "approve",
        "reviewer",
        "Relevant source.",
        queue_dir,
        reviews_file,
        AS_OF,
        source_checked=True,
    )
    result = prepare_knowledge_candidates(
        queue_dir=queue_dir,
        reviews_file=reviews_file,
        output_dir=tmp_path / "output",
        as_of=AS_OF,
    )

    content = Path(result["output"]).read_text(encoding="utf-8")
    assert result["approved_candidates"] == 1
    assert "Evidence status: **UNVERIFIED**" in content
    assert "https://example.org/case-study" in content
    assert "reviewer" in content
    assert "Source checked: https://example.org/case-study" in content


def test_no_approved_claims_produces_empty_candidate_bundle(tmp_path: Path):
    queue_dir, reviews_file = setup_queue(tmp_path)
    record_claim_review(
        CLAIM_ID,
        "needs-evidence",
        "reviewer",
        "Need methodology.",
        queue_dir,
        reviews_file,
        AS_OF,
        source_checked=True,
    )
    result = prepare_knowledge_candidates(
        queue_dir=queue_dir,
        reviews_file=reviews_file,
        output_dir=tmp_path / "output",
        as_of=AS_OF,
    )
    assert result["approved_candidates"] == 0
    assert "No claims have been approved" in Path(result["output"]).read_text(encoding="utf-8")


def test_later_review_decision_supersedes_earlier_decision(tmp_path: Path):
    queue_dir, reviews_file = setup_queue(tmp_path)
    record_claim_review(
        CLAIM_ID,
        "approve",
        "reviewer",
        "Initially approved.",
        queue_dir,
        reviews_file,
        AS_OF,
        source_checked=True,
    )
    record_claim_review(
        CLAIM_ID,
        "reject",
        "reviewer",
        "New source context invalidates it.",
        queue_dir,
        reviews_file,
        AS_OF,
        source_checked=True,
    )
    result = prepare_knowledge_candidates(
        queue_dir=queue_dir,
        reviews_file=reviews_file,
        output_dir=tmp_path / "output",
        as_of=AS_OF,
    )
    assert result["approved_candidates"] == 0
    assert len(reviews_file.read_text(encoding="utf-8").splitlines()) == 2


def test_regenerated_claim_queue_reflects_latest_human_decision(tmp_path: Path):
    from oai_intelligence.claims import generate_claim_review_queue

    data_dir = tmp_path / "observations"
    data_dir.mkdir()
    source_observation = {
        "schema_version": 1,
        "observation_id": "observation-live",
        "source_record_id": "rss:feed:article-1",
        "source": {
            "source_id": "rss",
            "source_type": "article",
            "url": "https://example.org/article",
            "title": "Architecture report",
            "publisher": "Example Engineering",
            "publisher_type": "editorial",
            "content_excerpt": (
                "The microservices architecture improved independent deployment speed "
                "across product teams by reducing release coordination."
            ),
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
    (data_dir / f"{AS_OF.isoformat()}.jsonl").write_text(
        json.dumps(source_observation) + "\n", encoding="utf-8"
    )
    queue_dir = tmp_path / "queue"
    reviews_file = tmp_path / "reviews.jsonl"
    result = generate_claim_review_queue(data_dir, queue_dir, AS_OF, reviews_file)
    claim = json.loads(Path(result["json"]).read_text(encoding="utf-8"))[0]
    record_claim_review(
        claim["claim_id"],
        "approve",
        "reviewer",
        "Source and context checked.",
        queue_dir,
        reviews_file,
        AS_OF,
        source_checked=True,
    )
    refreshed = generate_claim_review_queue(data_dir, queue_dir, AS_OF, reviews_file)
    refreshed_claim = json.loads(Path(refreshed["json"]).read_text(encoding="utf-8"))[0]

    assert refreshed_claim["review_status"] == "approve"
    assert refreshed_claim["reviewer"] == "reviewer"


def test_candidate_preparation_includes_approved_claims_from_earlier_daily_queues(tmp_path: Path):
    queue_dir, reviews_file = setup_queue(tmp_path)
    claim_json = (queue_dir / f"{AS_OF.isoformat()}.json").read_text(encoding="utf-8")
    earlier_date = date(2026, 11, 12)
    (queue_dir / f"{earlier_date.isoformat()}.json").write_text(claim_json, encoding="utf-8")
    record_claim_review(
        CLAIM_ID,
        "approve",
        "reviewer",
        "Checked the earlier source.",
        queue_dir,
        reviews_file,
        earlier_date,
        source_checked=True,
    )
    (queue_dir / f"{AS_OF.isoformat()}.json").write_text("[]", encoding="utf-8")

    result = prepare_knowledge_candidates(
        queue_dir=queue_dir,
        reviews_file=reviews_file,
        output_dir=tmp_path / "output",
        as_of=AS_OF,
    )

    assert result["queue_claims"] == 1
    assert result["approved_candidates"] == 1
    assert CLAIM_ID in Path(result["output"]).read_text(encoding="utf-8")
