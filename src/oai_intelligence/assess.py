"""Conservative evidence assessment without automatically upgrading claims."""

import json
import re
from collections import defaultdict
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from oai_intelligence.reports import load_observations
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


def _normalized_claim(claim: str) -> str:
    return re.sub(r"\s+", " ", claim.casefold()).strip()


def _publisher_domain(url: str) -> str:
    hostname = (urlsplit(url).hostname or "").casefold()
    return hostname.removeprefix("www.")


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def assess_observations(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Assess provenance, source activity, corroboration, and benchmark completeness."""
    claim_sources: dict[tuple[str, tuple[str, ...], str], set[str]] = defaultdict(set)
    for record in records:
        source = record.get("source", {})
        claim = _normalized_claim(record.get("claim", ""))
        architectures = tuple(sorted(set(record.get("architecture_matches", []))))
        claim_type = record.get("claim_type", "other")
        domain = _publisher_domain(source.get("url", ""))
        if claim and domain:
            claim_sources[(claim, architectures, claim_type)].add(domain)

    assessments: list[dict[str, Any]] = []
    for record in records:
        source = record.get("source", {})
        metrics = record.get("metrics", {})
        evidence = record.get("evidence_details", {})
        claim = _normalized_claim(record.get("claim", ""))
        architectures = tuple(sorted(set(record.get("architecture_matches", []))))
        claim_type = record.get("claim_type", "other")
        domain = _publisher_domain(source.get("url", ""))
        independent_domains = sorted(
            claim_sources.get((claim, architectures, claim_type), set()) - {domain}
        )
        missing_benchmark_fields = [
            field for field in BENCHMARK_FIELDS if not _has_value(evidence.get(field))
        ]
        is_performance = claim_type == "performance_claim" or source.get("source_type") == "benchmark"
        is_rejected = record.get("evidence_status") == "rejected"

        if is_rejected:
            disposition = "rejected_existing_record"
            rationale = "The observation is already marked rejected; this assessment does not reverse that decision."
        elif is_performance and missing_benchmark_fields:
            disposition = "benchmark_incomplete"
            rationale = "Performance evidence is incomplete; missing methodology fields prevent a meaningful comparison."
        elif is_performance:
            disposition = "benchmark_ready_for_human_review"
            rationale = "All required benchmark fields are present, but their accuracy and methodology still require human review."
        elif independent_domains:
            disposition = "independent_source_match"
            rationale = "An exact matching claim appears on another publisher domain; this is a corroboration lead, not proof."
        else:
            disposition = "unverified"
            rationale = "No independent exact-claim match or complete benchmark record was identified."

        assessments.append(
            {
                "observation_id": record.get("observation_id", ""),
                "source_record_id": record.get("source_record_id", ""),
                "source_domain": domain or None,
                "claim_type": claim_type,
                "architecture_matches": list(architectures),
                "source_activity": {
                    "stars": metrics.get("stars"),
                    "forks": metrics.get("forks"),
                    "discussion_points": metrics.get("points"),
                    "discussion_comments": metrics.get("comment_count"),
                    "interpretation": "discovery metadata only; not evidence of technical correctness or performance",
                },
                "independent_matching_domains": independent_domains,
                "benchmark": {
                    "applicable": is_performance,
                    "missing_fields": missing_benchmark_fields if is_performance else [],
                    "complete": is_performance and not missing_benchmark_fields,
                },
                "original_evidence_status": record.get("evidence_status", "unknown"),
                "disposition": disposition,
                "rationale": rationale,
                "assessed_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
            }
        )
    return assessments


def render_evidence_summary(assessments: list[dict[str, Any]], as_of: date) -> tuple[str, dict[str, Any]]:
    counts: dict[str, int] = {}
    for assessment in assessments:
        disposition = assessment["disposition"]
        counts[disposition] = counts.get(disposition, 0) + 1
    data = {
        "as_of": as_of.isoformat(),
        "assessment_count": len(assessments),
        "dispositions": dict(sorted(counts.items())),
        "benchmark_ready_for_human_review": counts.get("benchmark_ready_for_human_review", 0),
        "benchmark_incomplete": counts.get("benchmark_incomplete", 0),
        "independent_source_matches": counts.get("independent_source_match", 0),
        "note": "Assessments are review guidance. They do not alter original observations or promote evidence status.",
    }
    lines = [
        f"# Evidence Assessment Summary - {as_of.isoformat()}",
        "",
        f"**Observations assessed:** {len(assessments)}",
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
        "- An exact claim match across publisher domains is a lead for review, not proof that the claim is true.",
        "- Stars, forks, points, and comments are source-activity metadata, never performance evidence.",
        "- Benchmark completeness checks field presence only. It does not validate experimental quality, correctness, or reproducibility.",
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
    records = load_observations(data_dir or root / "data" / "observations")
    assessments = assess_observations(records)
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
        "dispositions": summary["dispositions"],
        "jsonl": str(jsonl_path),
        "json": str(json_path),
        "markdown": str(markdown_path),
    }
