import json
from datetime import date
from pathlib import Path

import pytest

from oai_intelligence.reports import generate_trend_report, load_observations, render_trend_report


def observation(day, architecture="microservices", source="github", ecosystem="java", source_record_id=None):
    return {
        "observation_id": f"{source}:{day}:{architecture}",
        "source_record_id": source_record_id or f"{source}:{day}:{architecture}",
        "observed_at": f"{day}T12:00:00Z",
        "architecture_matches": [architecture],
        "source": {"source_id": source, "source_type": "repository"},
        "ecosystem": ecosystem,
        "evidence_status": "unverified",
    }


def test_daily_report_counts_unique_source_records_and_avoids_delta_claims():
    records = [
        observation("2026-11-12", "microservices"),
        observation("2026-11-13", "microservices"),
        observation("2026-11-13", "clean-architecture", "rss", "cross_ecosystem"),
    ]
    markdown, data = render_trend_report(records, "daily", date(2026, 11, 13))

    assert data["current"]["raw_observation_count"] == 2
    assert data["current"]["observation_count"] == 2
    assert data["current"]["architecture_mentions"] == {
        "clean-architecture": 1,
        "microservices": 1,
    }
    assert "not representative estimates" in markdown
    assert "No period-over-period deltas" in markdown
    assert "No performance conclusion" in markdown


def test_weekly_window_counts_each_source_record_once():
    records = [
        observation("2026-11-07", source_record_id="github:org:repo-a"),
        observation("2026-11-07", source_record_id="github:org:repo-a"),
        observation("2026-11-13", source_record_id="github:org:repo-b"),
        observation("2026-11-05"),
    ]
    _, data = render_trend_report(records, "weekly", date(2026, 11, 13))

    assert data["current"]["raw_observation_count"] == 3
    assert data["current"]["observation_count"] == 2
    assert data["current"]["unique_source_records"] == 2


def test_each_architecture_is_counted_once_per_source_record():
    record = observation("2026-11-13")
    record["architecture_matches"] = ["microservices", "microservices"]
    _, data = render_trend_report([record], "daily", date(2026, 11, 13))
    assert data["current"]["architecture_mentions"]["microservices"] == 1


def test_invalid_period_is_rejected():
    with pytest.raises(ValueError, match="period"):
        render_trend_report([], "monthly", date(2026, 11, 13))


def test_invalid_jsonl_is_not_silently_ignored(tmp_path: Path):
    (tmp_path / "broken.jsonl").write_text("{bad json}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="broken.jsonl:1"):
        load_observations(tmp_path)


def test_generate_writes_markdown_and_json(tmp_path: Path):
    data_dir = tmp_path / "observations"
    data_dir.mkdir()
    record = observation("2026-11-13")
    (data_dir / "2026-11-13.jsonl").write_text(json.dumps(record) + "\n", encoding="utf-8")

    result = generate_trend_report(
        "daily",
        date(2026, 11, 13),
        data_dir=data_dir,
        output_dir=tmp_path / "reports",
    )

    assert result["observations_loaded"] == 1
    assert result["observations_in_period"] == 1
    assert result["raw_observations_in_period"] == 1
    assert Path(result["markdown"]).exists()
    assert Path(result["json"]).exists()

