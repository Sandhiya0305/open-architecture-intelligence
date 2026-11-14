"""Sample-aware summaries of collected architecture observations."""

import json
from collections import Counter
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any, cast

from jsonschema import ValidationError

from oai_intelligence.jsonl import iter_jsonl_objects
from oai_intelligence.migrations import migrate_observation_record
from oai_intelligence.types import ObservationRecord
from oai_intelligence.validation import PROJECT_ROOT, validate_observation


def load_observations(data_dir: Path, as_of: date | None = None) -> list[ObservationRecord]:
    """Load, migrate, and validate append-only JSONL observations."""
    records: list[ObservationRecord] = []
    if not data_dir.exists():
        return records
    for path in sorted(data_dir.glob("*.jsonl")):
        if as_of is not None and path.stem > as_of.isoformat():
            continue
        for line_number, record in iter_jsonl_objects(path):
            try:
                migrated = migrate_observation_record(record)
                validate_observation(migrated)
            except (TypeError, ValueError, ValidationError) as exc:
                raise ValueError(f"Invalid observation in {path}:{line_number}: {exc}") from exc
            records.append(cast(ObservationRecord, migrated))
    return records


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError(f"Timestamp must include a timezone: {value}")
    return parsed.astimezone(UTC)


def _period_counts(
    records: list[ObservationRecord], start: datetime, end: datetime
) -> dict[str, Any]:
    raw_selected: list[ObservationRecord] = [
        item for item in records if start <= _parse_timestamp(item["observed_at"]) < end
    ]

    # A source can be observed on several days. Keep its latest snapshot once per window.
    latest_by_source: dict[str, ObservationRecord] = {}
    for index, item in enumerate(raw_selected):
        source_key = str(
            item.get("source_record_id") or item.get("observation_id") or f"record:{index}"
        )
        current = latest_by_source.get(source_key)
        if current is None or _parse_timestamp(item["observed_at"]) > _parse_timestamp(
            current["observed_at"]
        ):
            latest_by_source[source_key] = item
    selected = list(latest_by_source.values())

    architectures: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    ecosystems: Counter[str] = Counter()
    evidence: Counter[str] = Counter()
    source_types: Counter[str] = Counter()

    for item in selected:
        architectures.update(set(item.get("architecture_matches", [])))
        sources[item.get("source", {}).get("source_id", "unknown")] += 1
        ecosystems[item.get("ecosystem", "unknown")] += 1
        evidence[item.get("evidence_status", "unknown")] += 1
        source_types[item.get("source", {}).get("source_type", "unknown")] += 1

    return {
        "raw_observation_count": len(raw_selected),
        "observation_count": len(selected),
        "unique_source_records": len(selected),
        "architecture_mentions": dict(sorted(architectures.items())),
        "by_source": dict(sorted(sources.items())),
        "by_ecosystem": dict(sorted(ecosystems.items())),
        "by_evidence_status": dict(sorted(evidence.items())),
        "by_source_type": dict(sorted(source_types.items())),
    }


def _format_counts(title: str, counts: dict[str, int]) -> list[str]:
    lines = [f"### {title}"]
    if not counts:
        return lines + ["- No observations in this period."]
    return [*lines, *(f"- {key}: {value}" for key, value in counts.items())]


def render_trend_report(
    records: list[ObservationRecord], period: str, as_of: date
) -> tuple[str, dict[str, Any]]:
    """Render a sample snapshot; it intentionally makes no trend or adoption inference."""
    if period not in {"daily", "weekly"}:
        raise ValueError("period must be 'daily' or 'weekly'")
    days = 1 if period == "daily" else 7
    end = datetime.combine(as_of + timedelta(days=1), time.min, tzinfo=UTC)
    start = end - timedelta(days=days)
    current = _period_counts(records, start, end)
    report_data = {
        "period": period,
        "period_start": start.isoformat(),
        "period_end_exclusive": end.isoformat(),
        "current": current,
    }

    heading = "Daily" if period == "daily" else "Rolling seven-day"
    lines = [
        f"# {heading} Architecture Observation Snapshot - {as_of.isoformat()}",
        "",
        f"**Window:** {start.date().isoformat()} to {as_of.isoformat()} (UTC, inclusive).",
        "",
        "## Scope and interpretation",
        "",
        f"- Raw collected observations in this window: **{current['raw_observation_count']}**.",
        f"- Unique source records represented: **{current['unique_source_records']}**.",
        "- Repeated snapshots of the same source record are counted once, using the latest snapshot in the window.",
        "- Collection is capped per query/feed. GitHub discovery is ordered by recently updated repositories.",
        "- These counts describe the collected sample only. They are not representative estimates of developer interest, adoption, market share, or architecture quality.",
        "- No period-over-period deltas are reported because collection limits and source ordering make those changes unsuitable as trend estimates.",
        "- Repository stars, forks, and discussion activity are not performance measurements.",
        "",
        "## Architecture mentions",
        "",
    ]
    lines.extend(
        [f"- {key}: {value}" for key, value in current["architecture_mentions"].items()]
        or ["- No classified architecture mentions in this period."]
    )
    lines += ["", *_format_counts("Unique source records by source", current["by_source"]), ""]
    lines += _format_counts("Unique source records by ecosystem", current["by_ecosystem"])
    lines += [""]
    lines += _format_counts("Evidence status", current["by_evidence_status"])
    lines += [""]
    lines += _format_counts("Source type", current["by_source_type"])
    lines += [
        "",
        "## Performance evidence",
        "",
        "No performance conclusion is generated by this report. Performance comparisons require workload, environment, versions, methodology, results, measurement date, and a traceable source.",
        "",
    ]
    return "\n".join(lines), report_data


def generate_trend_report(
    period: str = "daily",
    as_of: date | None = None,
    data_dir: Path | None = None,
    output_dir: Path | None = None,
    root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Generate Markdown and JSON sample snapshots from observation history."""
    report_date = as_of or datetime.now(UTC).date()
    records = load_observations(data_dir or root / "data" / "observations")
    markdown, report_data = render_trend_report(records, period, report_date)
    destination = output_dir or root / "reports" / period
    destination.mkdir(parents=True, exist_ok=True)
    stem = report_date.isoformat()
    markdown_path = destination / f"{stem}.md"
    json_path = destination / f"{stem}.json"
    markdown_path.write_text(markdown, encoding="utf-8")
    json_path.write_text(json.dumps(report_data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "period": period,
        "as_of": stem,
        "observations_loaded": len(records),
        "observations_in_period": report_data["current"]["observation_count"],
        "raw_observations_in_period": report_data["current"]["raw_observation_count"],
        "markdown": str(markdown_path),
        "json": str(json_path),
    }
