from datetime import date
from pathlib import Path

import pytest

from oai_intelligence import publishing
from oai_intelligence.publishing import PublishingError, publish_knowledge_candidates


def valid_bundle(path: Path) -> Path:
    path.write_text(
        "# Reviewed candidates\n\n"
        "> Evidence status: UNVERIFIED. Human approval here is editorial only.\n\n"
        "- Claim ID: `claim-1`\n"
        "- Human review: reviewer\n"
        "- Source: [source](https://example.org/source)\n",
        encoding="utf-8",
    )
    return path


def test_publish_requires_cross_repository_token_before_git_changes(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("OAI_GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    bundle = valid_bundle(tmp_path / "bundle.md")
    repo = tmp_path / "knowledge"
    repo.mkdir()
    with pytest.raises(PublishingError, match="OAI_GITHUB_TOKEN"):
        publish_knowledge_candidates(bundle, repo)


def test_publish_rejects_bundle_without_safety_label(tmp_path: Path):
    bundle = tmp_path / "bundle.md"
    bundle.write_text("# Claims\n\nLooks good.\n", encoding="utf-8")
    with pytest.raises(PublishingError, match="safeguards"):
        publish_knowledge_candidates(bundle, tmp_path, token="test-token")


def test_publish_creates_draft_pr_from_expected_knowledge_repo(tmp_path: Path, monkeypatch):
    bundle = valid_bundle(tmp_path / "bundle.md")
    repo = tmp_path / "knowledge"
    (repo / ".git").mkdir(parents=True)
    git_calls = []

    def fake_git(repo_path, *args):
        git_calls.append(args)
        if args == ("remote", "get-url", "origin"):
            return "https://github.com/Sandhiya0305/open-architecture-knowledge.git"
        return ""

    def fake_request(url, token, payload):
        assert token == "test-token"
        assert payload["draft"] is True
        assert payload["base"] == "main"
        return {"html_url": "https://github.com/Sandhiya0305/open-architecture-knowledge/pull/42"}

    monkeypatch.setattr(publishing, "_git", fake_git)
    monkeypatch.setattr(publishing, "_github_request", fake_request)
    result = publish_knowledge_candidates(
        bundle, repo, token="test-token", as_of=date(2026, 11, 13)
    )

    assert result["pull_request_url"].endswith("/pull/42")
    assert result["branch"] == "oai/knowledge-candidates-20261113"
    created = repo / "evidence" / "candidates" / "2026-11-13.md"
    assert created.exists()
    assert any(call[:2] == ("push", "--set-upstream") for call in git_calls)


def test_publish_refuses_dirty_knowledge_repo(tmp_path: Path, monkeypatch):
    bundle = valid_bundle(tmp_path / "bundle.md")
    repo = tmp_path / "knowledge"
    (repo / ".git").mkdir(parents=True)

    def fake_git(repo_path, *args):
        if args == ("status", "--porcelain"):
            return "M README.md"
        return "https://github.com/Sandhiya0305/open-architecture-knowledge.git"

    monkeypatch.setattr(publishing, "_git", fake_git)
    with pytest.raises(PublishingError, match="uncommitted changes"):
        publish_knowledge_candidates(bundle, repo, token="test-token")
