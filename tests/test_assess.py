import json
from datetime import date
from pathlib import Path

from oai_intelligence.assess import assess_observations, generate_evidence_assessment
from oai_intelligence.validation import validate_observation


def record(
    observation_id: str,
    domain: str,
    claim: str = "The microservices architecture improved request latency by 20 percent.",
    claim_type: str = "performance_claim",
    evidence_details=None,
):
    return {
        "observation_id": observation_id,
        "source_record_id": f"{domain}:{observation_id}",
        "source": {
            "source_id": domain,
            "source_type": "article",
            "url": f"https://{domain}/article",
            "title": "Architecture report",
            "content_excerpt": claim,
            "published_at": None,
            "retrieved_at": "2026-11-13T00:00:00Z",
        },
        "observed_at": "2026-11-13T00:00:00Z",
        "category": "microservices",
        "architecture_matches": ["microservices"],
        "ecosystem": "cross_ecosystem",
        "claim": "Repository metadata matched configured architecture discovery terms.",
        "claim_type": claim_type,
        "evidence_status": "unverified",
        "evidence_notes": "Needs review.",
        "evidence_details": evidence_details or {},
        "tags": [],
        "metrics": {"stars": 500, "points": 80},
    }


def test_performance_claim_missing_methodology_fields_is_incomplete():
    assessment = assess_observations([record("a", "example.com")])[0]

    assert assessment["disposition"] == "benchmark_incomplete"
    assert "workload" in assessment["benchmark"]["missing_fields"]
    assert "methodology" in assessment["benchmark"]["missing_fields"]
    assert assessment["source_activity"]["stars"] == 500
    assert "not evidence" in assessment["source_activity"]["interpretation"]


def test_complete_benchmark_is_only_ready_for_human_review():
    details = {
        "workload": "1000 requests per second, 50 KB payload",
        "environment": "Linux test VM",
        "hardware": "8 vCPU, 16 GB RAM",
        "software_versions": "Runtime 22, framework 5.1",
        "methodology": "Repeated test, 10 runs, median reported",
        "results": {"p95_latency_ms": 42},
        "measurement_date": "2026-11-10",
        "source_url": "https://benchmarks.example.com/run-1",
    }
    assessment = assess_observations(
        [record("a", "benchmark.example", evidence_details=details)]
    )[0]

    assert assessment["disposition"] == "benchmark_complete_for_human_review"
    assert assessment["benchmark"]["complete"] is True


def test_exact_architecture_statement_on_different_hosts_is_only_a_review_lead():
    statement = "The microservices architecture improved request latency by 20 percent."
    records = [
        record("a", "publisher-one.example", claim=statement, claim_type="architecture_description"),
        record("b", "publisher-two.example", claim=statement, claim_type="architecture_description"),
    ]
    results = assess_observations(records)

    assert all(item["disposition"] == "cross_host_match_review_lead" for item in results)
    assert results[0]["matching_source_hosts"] == ["publisher-two.example"]
    assert "independent ownership" in results[0]["rationale"]


def test_same_host_does_not_count_as_cross_host_match():
    statement = "The microservices architecture improved request latency by 20 percent."
    records = [
        record("a", "same.example", claim=statement, claim_type="architecture_description"),
        record("b", "same.example", claim=statement, claim_type="architecture_description"),
    ]
    results = assess_observations(records)

    assert all(item["disposition"] == "unverified_extracted_statement" for item in results)
    assert all(item["matching_source_hosts"] == [] for item in results)


def test_different_claims_do_not_match():
    records = [
        record("a", "publisher-one.example", claim="The microservices architecture improved request latency by 20 percent."),
        record("b", "publisher-two.example", claim="The layered architecture improved maintainability across teams."),
    ]
    results = assess_observations(records)

    assert all(item["disposition"] == "benchmark_incomplete" for item in results)
    assert all(item["matching_source_hosts"] == [] for item in results)


def test_boilerplate_observation_claim_is_not_used_as_evidence():
    item = record("a", "example.com", claim="The weather was sunny yesterday.", claim_type="architecture_description")
    item["claim"] = "A repository matched configured search terms."

    assessment = assess_observations([item])[0]

    assert assessment["disposition"] == "no_extractable_architecture_statement"
    assert assessment["extracted_statements"] == []


def test_rejected_record_remains_rejected():
    rejected = record("a", "example.com")
    rejected["evidence_status"] = "rejected"

    result = assess_observations([rejected])[0]

    assert result["disposition"] == "rejected_existing_record"
    assert result["original_evidence_status"] == "rejected"


def test_assessment_does_not_mutate_original_observation():
    original = record("a", "example.com")
    before = json.dumps(original, sort_keys=True)

    assess_observations([original])

    assert json.dumps(original, sort_keys=True) == before


def test_optional_benchmark_details_validate_against_observation_schema():
    details = {
        "workload": "HTTP load test",
        "environment": "Linux",
        "hardware": "8 vCPU",
        "software_versions": "Runtime 22",
        "methodology": "10 repeated runs",
        "results": "p95 latency 42 ms",
        "measurement_date": "2026-11-10",
        "source_url": "https://benchmarks.example.com/run-1",
    }
    validate_observation(record("a", "benchmark.example", evidence_details=details))


def test_generate_assessments_writes_jsonl_and_summary(tmp_path: Path):
    data_dir = tmp_path / "observations"
    data_dir.mkdir()
    observation = record("a", "example.com")
    (data_dir / "2026-11-13.jsonl").write_text(
        json.dumps(observation) + "\n", encoding="utf-8"
    )

    result = generate_evidence_assessment(
        data_dir=data_dir,
        output_dir=tmp_path / "evidence",
        as_of=date(2026, 11, 13),
    )

    assert result["assessments_written"] == 1
    assert result["extracted_statements"] == 1
    assert Path(result["jsonl"]).exists()
    assert Path(result["json"]).exists()
    assert Path(result["markdown"]).exists()
