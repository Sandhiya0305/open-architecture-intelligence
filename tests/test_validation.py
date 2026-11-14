from pathlib import Path

from oai_intelligence import validation


def test_packaged_configuration_and_schemas_match_repository_sources():
    package_resources = Path(validation.__file__).parent / "resources"
    for category in ("config", "schema"):
        source_dir = validation.PROJECT_ROOT / category
        packaged_dir = package_resources / category
        for source in source_dir.iterdir():
            if source.is_file():
                packaged = packaged_dir / source.name
                assert packaged.is_file()
                assert packaged.read_bytes() == source.read_bytes()


def test_validation_uses_bundled_resources_when_given_an_external_data_directory(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        validation,
        "CONFIG_ROOT",
        Path(validation.__file__).parent / "resources",
    )

    validation.validate_project_configs(tmp_path)


def test_schema_identifiers_are_stable_and_versioned():
    import json

    schema_dir = validation.PROJECT_ROOT / "schema"
    expected = {
        "observation.schema.json": "urn:oai:observation:v1",
        "claim.schema.json": "urn:oai:claim:v1",
        "review-decision.schema.json": "urn:oai:review-decision:v1",
    }
    for filename, schema_id in expected.items():
        schema = json.loads((schema_dir / filename).read_text(encoding="utf-8"))
        assert schema["$id"] == schema_id
