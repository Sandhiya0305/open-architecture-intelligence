import json
from datetime import date
from pathlib import Path

from oai_intelligence.assess import (
    assess_observations,
    generate_evidence_assessment,
)
from oai_intelligence.validation import validate_observation


def record(
    observation_id: str,
    domain: str,
    claim: str = "The system reduced request latency by 20 percent.",
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
            "published_at": None,
            "retrieved_at": "2026-11-13T00:00:00Z",
        },
        "observed_at": "2026-11-13T00:00:00Z",
        "category": "microservices",
        "architecture_matches": ["microservices"],
        "ecosystem": "cross_ecosystem",
        "claim": claim,
        "claim_type": claim_type,
        "evidence_status": "unverified",
        "evidence_notes": "Needs review.",
        "evidence_details": evidence_details or {},
        "tags": [],
        "metrics": {"stars": 500, "points": 80},
    }


def test_performance_claim_missing_methodology_fields_is_incomplete():
    results = assess_observations([record("a", "example.com")])
    assessment = results[0]

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
    results = assess_observations([record("a", "benchmark.example", evidence_details=details)])

    assert results[0]["disposition"] == "benchmark_ready_for_human_review"
    assert results[0]["benchmark"]["complete"] is True


def test_exact_claim_on_independent_domains_is_only_a_review_lead():
    records = [
        record("a", "publisher-one.example", claim_type="architecture_description"),
        record("b", "publisher-two.example", claim_type="architecture_description"),
    ]
    results = assess_observations(records)

    assert all(item["disposition"] == "independent_source_match" for item in results)
    assert results[0]["independent_matching_domains"] == ["publisher-two.example"]


def test_same_publisher_does_not_count_as_independent_corroboration():
    records = [
        record("a", "same.example", claim_type="architecture_description"),
        record("b", "same.example", claim_type="architecture_description"),
    ]
    results = assess_observations(records)

    assert all(item["disposition"] == "unverified" for item in results)


def test_different_claims_do_not_corroborate_each_other():
    records = [
        record("a", "publisher-one.example", claim="Architecture A improves throughput."),
        record("b", "publisher-two.example", claim="Architecture B improves throughput."),
    ]
    results = assess_observations(records)

    assert all(item["disposition"] == "benchmark_incomplete" for item in results)


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
    assert Path(result["jsonl"]).exists()
    assert Path(result["json"]).exists()
    assert Path(result["markdown"]).exists()
