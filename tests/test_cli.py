import pytest

from oai_intelligence.cli import build_parser, main


def test_review_command_requires_source_checked_attestation():
    parser = build_parser()
    with pytest.raises(SystemExit) as error:
        parser.parse_args([
            "claims", "review", "a" * 64,
            "--decision", "approve",
            "--reviewer", "reviewer",
            "--note", "Checked the source.",
        ])
    assert error.value.code == 2


def test_review_command_accepts_explicit_source_checked_attestation():
    args = build_parser().parse_args([
        "claims", "review", "a" * 64,
        "--decision", "approve",
        "--reviewer", "reviewer",
        "--note", "Checked the source.",
        "--source-checked",
    ])
    assert args.source_checked is True


def test_validate_config_command_succeeds(capsys):
    assert main(["validate-config"]) == 0
    assert "Configuration is valid." in capsys.readouterr().out


def test_invalid_discovery_limit_fails_without_network_access(capsys):
    assert main(["discover", "github", "--limit", "0"]) == 1
    assert "--limit must be between 1 and 100" in capsys.readouterr().err
