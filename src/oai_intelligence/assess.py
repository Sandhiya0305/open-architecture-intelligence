"""Assess source-linked architecture statements without automatically verifying them."""

import json
from collections import defaultdict
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from oai_intelligence.claims import extract_claim_candidates
from oai_intelligence.reports import load_observations
from oai_intelligence.types import ClaimCandidate, ObservationRecord
from oai_intelligence.validation import PROJECT_ROOT

BENCHMARK_FIELDS = (
    "workload",
    "environment",
    "hardware",
    "software_versions",
    "methodology",
    "results",
    "measurement_date",
    "source_url",
)


def _publisher_host(url: str) -> str:
    return (urlsplit(url).hostname or "").casefold().removeprefix("www.")


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def assess_observations(
    records: list[ObservationRecord],
    target_observation_ids: set[str] | None = None,
    assessment_date: date | None = None,
) -> list[dict[str, Any]]:
    """Assess extracted article statements and benchmark completeness, not boilerplate claims."""
    extracted_by_observation: dict[str, list[ClaimCandidate]] = {}
    statement_hosts: dict[tuple[str, tuple[str, ...]], set[str]] = defaultdict(set)

    for record in records:
        observation_id = str(record.get("observation_id") or "")
        candidates = extract_claim_candidates(record)
        extracted_by_observation[observation_id] = candidates
        host = _publisher_host(str(record.get("source", {}).get("url") or ""))
        for candidate in candidates:
            key = (candidate["normalized_claim"], tuple(candidate["architecture_ids"]))
            if host:
                statement_hosts[key].add(host)

    assessments: list[dict[str, Any]] = []
    assessment_records = (
        records
        if target_observation_ids is None
        else [
            record
            for record in records
            if str(record.get("observation_id") or "") in target_observation_ids
        ]
    )
    for record in assessment_records:
        source = record.get("source", {})
        metrics = record.get("metrics", {})
        evidence = record.get("evidence_details", {})
        candidates = extracted_by_observation.get(str(record.get("observation_id") or ""), [])
        host = _publisher_host(str(source.get("url") or ""))
        matching_hosts: set[str] = set()
        for candidate in candidates:
            key = (candidate["normalized_claim"], tuple(candidate["architecture_ids"]))
            matching_hosts.update(statement_hosts.get(key, set()) - ({host} if host else set()))

        claim_type = record.get("claim_type", "other")
        is_performance = (
            claim_type == "performance_claim" or source.get("source_type") == "benchmark"
        )
        missing_benchmark_fields = [
            field for field in BENCHMARK_FIELDS if not _has_value(evidence.get(field))
        ]
        original_status = record.get("evidence_status", "unknown")

        if original_status == "rejected":
            disposition = "rejected_existing_record"
            rationale = "The observation is already marked rejected; this assessment does not reverse that decision."
        elif is_performance and missing_benchmark_fields:
            disposition = "benchmark_incomplete"
            rationale = (
                "Performance evidence is incomplete. Required workload, environment, hardware, "
                "versions, methodology, results, measurement date, and source are not all present."
            )
        elif is_performance:
            disposition = "benchmark_complete_for_human_review"
            rationale = (
                "Required benchmark fields are present. Their accuracy, comparability, and "
                "methodological quality still require human review."
            )
        elif matching_hosts:
            disposition = "cross_host_match_review_lead"
            rationale = (
                "An exact extracted statement appears on other hostnames. This does not establish "
                "independent ownership, source independence, or truth."
            )
        elif candidates:
            disposition = "unverified_extracted_statement"
            rationale = (
                "An architecture-specific statement was extracted from article text. The full "
                "source, author perspective, context, and supporting evidence remain unreviewed."
            )
        else:
            disposition = "no_extractable_architecture_statement"
            rationale = (
                "No complete architecture-specific outcome, limitation, or decision statement "
                "was extracted. Repository metadata and discussion activity are not technical evidence."
            )

        assessments.append(
            {
                "observation_id": record.get("observation_id", ""),
                "source_record_id": record.get("source_record_id", ""),
                "source_host": host or None,
                "source_type": source.get("source_type"),
                "claim_type": claim_type,
                "architecture_matches": sorted(set(record.get("architecture_matches", []))),
                "extracted_statements": [
                    {
                        "claim_id": candidate["claim_id"],
                        "text": candidate["claim_text"],
                        "kinds": candidate["claim_kinds"],
                    }
                    for candidate in candidates
                ],
                "matching_source_hosts": sorted(matching_hosts),
                "source_activity": {
                    "stars": metrics.get("stars"),
                    "forks": metrics.get("forks"),
                    "discussion_points": metrics.get("points"),
                    "discussion_comments": metrics.get("comment_count"),
                    "interpretation": (
                        "discovery metadata only; not evidence of technical correctness, "
                        "architecture outcomes, or performance"
                    ),
                },
                "benchmark": {
                    "applicable": is_performance,
                    "missing_fields": missing_benchmark_fields if is_performance else [],
                    "complete": is_performance and not missing_benchmark_fields,
                    "provided_fields": sorted(
                        field for field in BENCHMARK_FIELDS if _has_value(evidence.get(field))
                    ),
                },
                "original_evidence_status": original_status,
                "disposition": disposition,
                "rationale": rationale,
                "assessment_date": assessment_date.isoformat() if assessment_date else None,
            }
        )
    return assessments


def render_evidence_summary(
    assessments: list[dict[str, Any]], as_of: date
) -> tuple[str, dict[str, Any]]:
    counts: dict[str, int] = {}
    extracted_count = 0
    for assessment in assessments:
        disposition = assessment["disposition"]
        counts[disposition] = counts.get(disposition, 0) + 1
        extracted_count += len(assessment["extracted_statements"])

    data = {
        "as_of": as_of.isoformat(),
        "assessment_count": len(assessments),
        "extracted_statement_count": extracted_count,
        "dispositions": dict(sorted(counts.items())),
        "benchmark_complete_for_human_review": counts.get("benchmark_complete_for_human_review", 0),
        "benchmark_incomplete": counts.get("benchmark_incomplete", 0),
        "cross_host_match_review_leads": counts.get("cross_host_match_review_lead", 0),
        "note": (
            "Assessments are review guidance. Hostname matches do not prove independent "
            "corroboration, and no assessment automatically changes evidence status."
        ),
    }
    lines = [
        f"# Evidence Assessment Summary - {as_of.isoformat()}",
        "",
        f"**Observations assessed:** {len(assessments)}",
        f"**Architecture-specific statements extracted:** {extracted_count}",
        "",
        "## Assessment outcomes",
        "",
    ]
    lines.extend(
        [f"- {key}: {value}" for key, value in sorted(counts.items())]
        or ["- No observations assessed."]
    )
    lines += [
        "",
        "## Interpretation safeguards",
        "",
        "- Original observations are immutable; assessment output is stored separately.",
        "- Extracted statements are leads for source review, not verified facts.",
        "- Matching hostnames do not establish independent ownership or corroboration.",
        "- Stars, forks, points, and comments are source-activity metadata, never performance evidence.",
        "- Benchmark completeness checks field presence only; it does not validate experimental quality or reproducibility.",
        "- No assessment automatically changes evidence_status or approves a knowledge-base update.",
        "",
    ]
    return "\n".join(lines), data


def generate_evidence_assessment(
    data_dir: Path | None = None,
    output_dir: Path | None = None,
    as_of: date | None = None,
    root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Write per-observation assessments plus a human-readable summary."""
    report_date = as_of or datetime.now(UTC).date()
    records = load_observations(data_dir or root / "data" / "observations", as_of=report_date)
    current_records = [
        record
        for record in records
        if datetime.fromisoformat(record["observed_at"]).astimezone(UTC).date() == report_date
    ]
    target_ids = {str(record["observation_id"]) for record in current_records}
    assessments = assess_observations(records, target_ids, report_date)
    markdown, summary = render_evidence_summary(assessments, report_date)
    destination = output_dir or root / "reports" / "evidence"
    destination.mkdir(parents=True, exist_ok=True)
    stem = report_date.isoformat()
    jsonl_path = destination / f"{stem}.jsonl"
    json_path = destination / f"{stem}.json"
    markdown_path = destination / f"{stem}.md"
    jsonl_path.write_text(
        "".join(json.dumps(item, sort_keys=True) + "\n" for item in assessments),
        encoding="utf-8",
    )
    json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(markdown, encoding="utf-8")
    return {
        "as_of": stem,
        "observations_loaded": len(records),
        "assessments_written": len(assessments),
        "extracted_statements": summary["extracted_statement_count"],
        "dispositions": summary["dispositions"],
        "jsonl": str(jsonl_path),
        "json": str(json_path),
        "markdown": str(markdown_path),
    }
