"""Deterministic, evidence-aware summaries of collected observations."""

import json
from collections import Counter
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any

from oai_intelligence.validation import PROJECT_ROOT


def load_observations(data_dir: Path) -> list[dict[str, Any]]:
    """Load JSONL observations in chronological source-independent order."""
    records: list[dict[str, Any]] = []
    if not data_dir.exists():
        return records
    for path in sorted(data_dir.glob("*.jsonl")):
        with path.open(encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, start=1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSON in {path}:{line_number}: {exc}") from exc
                if not isinstance(record, dict):
                    raise TypeError(f"Expected an observation object in {path}:{line_number}.")
                records.append(record)
    return records


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError(f"Timestamp must include a timezone: {value}")
    return parsed.astimezone(UTC)


def _period_counts(records: list[dict[str, Any]], start: datetime, end: datetime) -> dict[str, Any]:
    selected = [
        item for item in records
        if start <= _parse_timestamp(item["observed_at"]) < end
    ]
    architectures: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    ecosystems: Counter[str] = Counter()
    evidence: Counter[str] = Counter()
    source_types: Counter[str] = Counter()

    for item in selected:
        # Count each architecture at most once per observation.
        architectures.update(set(item.get("architecture_matches", [])))
        sources[item.get("source", {}).get("source_id", "unknown")] += 1
        ecosystems[item.get("ecosystem", "unknown")] += 1
        evidence[item.get("evidence_status", "unknown")] += 1
        source_types[item.get("source", {}).get("source_type", "unknown")] += 1

    return {
        "observation_count": len(selected),
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


def _comparison(current: dict[str, Any], previous: dict[str, Any]) -> list[str]:
    lines = ["## Change versus the previous equivalent period", ""]
    current_total = current["observation_count"]
    previous_total = previous["observation_count"]
    lines.append(
        f"- Observations: {current_total} "
        f"({'+' if current_total - previous_total >= 0 else ''}{current_total - previous_total} "
        f"versus {previous_total} previously)."
    )
    keys = sorted(set(current["architecture_mentions"]) | set(previous["architecture_mentions"]))
    if not keys:
        lines.append("- No architecture mentions in either period.")
    for key in keys:
        now = current["architecture_mentions"].get(key, 0)
        before = previous["architecture_mentions"].get(key, 0)
        delta = now - before
        lines.append(f"- {key}: {now} mentions ({'+' if delta >= 0 else ''}{delta} versus {before}).")
    return lines


def render_trend_report(
    records: list[dict[str, Any]], period: str, as_of: date
) -> tuple[str, dict[str, Any]]:
    """Render daily or rolling seven-day report and return its structured data."""
    if period not in {"daily", "weekly"}:
        raise ValueError("period must be 'daily' or 'weekly'")
    days = 1 if period == "daily" else 7
    end = datetime.combine(as_of + timedelta(days=1), time.min, tzinfo=UTC)
    start = end - timedelta(days=days)
    previous_start = start - timedelta(days=days)
    current = _period_counts(records, start, end)
    previous = _period_counts(records, previous_start, start)
    report_data = {
        "period": period,
        "period_start": start.isoformat(),
        "period_end_exclusive": end.isoformat(),
        "previous_period_start": previous_start.isoformat(),
        "previous_period_end_exclusive": start.isoformat(),
        "current": current,
        "previous": previous,
    }

    heading = "Daily" if period == "daily" else "Weekly"
    lines = [
        f"# {heading} Architecture Observation Report â€” {as_of.isoformat()}",
        "",
        f"**Window:** {start.date().isoformat()} to {as_of.isoformat()} (UTC, inclusive).",
        "",
        "## Scope and interpretation",
        "",
        f"- Collected observations in this window: **{current['observation_count']}**.",
        "- Architecture counts are classified mentions in collected records, not verified adoption, market share, or architecture quality.",
        "- Source and ecosystem counts describe this discovery sample; they are not representative population estimates.",
        "- Evidence labels reflect the stored review state. An unverified record is not a verified technical claim.",
        "- Repository stars, forks, and discussion activity are not performance measurements.",
        "",
        "## Architecture mentions",
        "",
    ]
    lines.extend(
        [f"- {key}: {value}" for key, value in current["architecture_mentions"].items()]
        or ["- No classified architecture mentions in this period."]
    )
    lines += ["", *_comparison(current, previous), ""]
    lines += _format_counts("Observations by source", current["by_source"])
    lines += [""]
    lines += _format_counts("Observations by ecosystem", current["by_ecosystem"])
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
    """Generate Markdown and JSON reports from the append-only observation history."""
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
        "markdown": str(markdown_path),
        "json": str(json_path),
    }
