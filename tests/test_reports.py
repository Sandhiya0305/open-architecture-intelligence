import json
from datetime import date
from pathlib import Path

import pytest

from oai_intelligence.reports import (
    generate_trend_report,
    load_observations,
    render_trend_report,
)


def observation(day, architecture="microservices", source="github", ecosystem="java"):
    return {
        "observed_at": f"{day}T12:00:00Z",
        "architecture_matches": [architecture],
        "source": {"source_id": source, "source_type": "repository"},
        "ecosystem": ecosystem,
        "evidence_status": "unverified",
    }


def test_daily_report_counts_mentions_and_compares_previous_day():
    records = [
        observation("2026-11-12", "microservices"),
        observation("2026-11-13", "microservices"),
        observation("2026-11-13", "clean-architecture", "rss", "cross_ecosystem"),
    ]
    markdown, data = render_trend_report(records, "daily", date(2026, 11, 13))

    assert data["current"]["observation_count"] == 2
    assert data["current"]["architecture_mentions"] == {
        "clean-architecture": 1,
        "microservices": 1,
    }
    assert data["previous"]["observation_count"] == 1
    assert "not verified adoption" in markdown
    assert "No performance conclusion" in markdown


def test_weekly_window_is_seven_days_and_excludes_older_records():
    records = [
        observation("2026-11-06"),
        observation("2026-11-07"),
        observation("2026-11-13"),
    ]
    _, data = render_trend_report(records, "weekly", date(2026, 11, 13))

    assert data["current"]["observation_count"] == 2
    assert data["previous"]["observation_count"] == 1


def test_each_architecture_is_counted_once_per_observation():
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
    assert Path(result["markdown"]).exists()
    assert Path(result["json"]).exists()
