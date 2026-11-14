import json

from oai_intelligence.storage import append_observations


def test_append_is_idempotent(tmp_path) -> None:
    destination = tmp_path / "observations.jsonl"
    records = [
        {"observation_id": "one", "claim": "first"},
        {"observation_id": "two", "claim": "second"},
    ]
    assert append_observations(destination, records) == 2
    assert append_observations(destination, records) == 0
    stored = [json.loads(line) for line in destination.read_text(encoding="utf-8").splitlines()]
    assert [record["observation_id"] for record in stored] == ["one", "two"]


def test_corrupt_jsonl_is_not_silently_overwritten(tmp_path) -> None:
    destination = tmp_path / "observations.jsonl"
    destination.write_text("{bad json}\n", encoding="utf-8")
    try:
        append_observations(destination, [{"observation_id": "new"}])
    except ValueError as exc:
        assert "Invalid JSONL" in str(exc)
    else:
        raise AssertionError("Expected corrupt history to be rejected.")


def test_new_snapshot_of_same_source_is_appended_once(tmp_path) -> None:
    destination = tmp_path / "observations.jsonl"
    original = {"observation_id": "snapshot-1", "source_record_id": "github:org/repo"}
    enriched = {"observation_id": "snapshot-2", "source_record_id": "github:org/repo"}

    assert append_observations(destination, [original]) == 1
    assert append_observations(destination, [enriched]) == 1
    assert append_observations(destination, [enriched]) == 0
    stored = [json.loads(line) for line in destination.read_text(encoding="utf-8").splitlines()]
    assert [record["observation_id"] for record in stored] == ["snapshot-1", "snapshot-2"]
