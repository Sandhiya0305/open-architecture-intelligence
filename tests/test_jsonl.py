import pytest

from oai_intelligence.jsonl import iter_jsonl_objects, read_jsonl_objects


def test_reads_jsonl_objects_with_line_numbers(tmp_path):
    path = tmp_path / "records.jsonl"
    path.write_text('\n{"id": 1}\n\n{"id": 2}\n', encoding="utf-8")

    assert list(iter_jsonl_objects(path)) == [(2, {"id": 1}), (4, {"id": 2})]
    assert read_jsonl_objects(path) == [{"id": 1}, {"id": 2}]


def test_missing_jsonl_file_is_empty(tmp_path):
    assert read_jsonl_objects(tmp_path / "missing.jsonl") == []


def test_invalid_jsonl_reports_path_and_line(tmp_path):
    path = tmp_path / "broken.jsonl"
    path.write_text("\n{bad json}\n", encoding="utf-8")

    with pytest.raises(ValueError, match=r"broken.jsonl:2"):
        read_jsonl_objects(path)


def test_non_object_jsonl_record_is_rejected(tmp_path):
    path = tmp_path / "records.jsonl"
    path.write_text("[1, 2]\n", encoding="utf-8")

    with pytest.raises(TypeError, match="JSON object"):
        read_jsonl_objects(path)
