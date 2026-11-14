import json
import subprocess
from datetime import date
from pathlib import Path

from oai_intelligence import publishing, review
from oai_intelligence.claims import generate_claim_review_queue
from oai_intelligence.publishing import publish_knowledge_candidates
from oai_intelligence.review import prepare_knowledge_candidates, record_claim_review

AS_OF = date(2026, 11, 13)


def _run_git(path: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=path, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def test_discover_review_and_publish_flow_is_site_visible(tmp_path: Path, monkeypatch):
    # Discover: persist a source-linked article observation and build a claim queue.
    data_dir = tmp_path / "observations"
    data_dir.mkdir()
    observation = {
        "schema_version": 1,
        "observation_id": "observation-1",
        "source_record_id": "rss:feed:architecture-article",
        "source": {
            "source_id": "rss",
            "source_type": "article",
            "url": "https://publisher.example/architecture",
            "title": "Microservices deployment case study",
            "publisher": "Example Engineering",
            "publisher_type": "editorial",
            "content_excerpt": (
                "The microservices architecture improved independent deployment speed "
                "across product teams by reducing release coordination."
            ),
            "published_at": None,
            "retrieved_at": "2026-11-13T00:00:00Z",
        },
        "observed_at": "2026-11-13T00:00:00Z",
        "category": "microservices",
        "architecture_matches": ["microservices"],
        "ecosystem": "cross_ecosystem",
        "claim": "Discovery metadata only.",
        "claim_type": "discovery_candidate",
        "evidence_status": "unverified",
        "evidence_notes": "Needs source review.",
        "tags": ["microservices"],
        "metrics": {},
    }
    (data_dir / "2026-11-13.jsonl").write_text(json.dumps(observation) + "\n", encoding="utf-8")
    queue_dir = tmp_path / "queue"
    reviews_file = tmp_path / "reviews" / "decisions.jsonl"
    queue_result = generate_claim_review_queue(
        data_dir=data_dir,
        output_dir=queue_dir,
        as_of=AS_OF,
        reviews_file=reviews_file,
    )
    queue = json.loads(Path(queue_result["json"]).read_text(encoding="utf-8"))
    assert len(queue) == 1
    claim_id = queue[0]["claim_id"]

    # Review: bind the decision to a verified GitHub identity and source-check attestation.
    monkeypatch.setenv("OAI_REVIEW_TOKEN", "review-token")
    monkeypatch.setattr(
        review,
        "_authenticated_github_user",
        lambda token: {"login": "reviewer", "id": 7654321},
    )
    decision = record_claim_review(
        claim_id,
        "approve",
        "reviewer",
        "Opened the original article and checked the stated architecture context.",
        queue_dir,
        reviews_file,
        AS_OF,
        source_checked=True,
    )
    assert decision["reviewer_id"] == 7654321

    bundle_result = prepare_knowledge_candidates(
        queue_dir=queue_dir,
        reviews_file=reviews_file,
        output_dir=tmp_path / "candidate-bundles",
        as_of=AS_OF,
    )
    bundle = Path(bundle_result["output"])
    assert bundle_result["approved_candidates"] == 1

    # Publish: use a real local Git branch/commit while mocking only the remote boundary.
    knowledge_repo = tmp_path / "knowledge"
    knowledge_repo.mkdir()
    _run_git(knowledge_repo, "init", "-b", "main")
    _run_git(knowledge_repo, "config", "user.name", "OAI integration test")
    _run_git(knowledge_repo, "config", "user.email", "oai-test@example.invalid")
    (knowledge_repo / "README.md").write_text("# Knowledge\n", encoding="utf-8")
    _run_git(knowledge_repo, "add", "README.md")
    _run_git(knowledge_repo, "commit", "-m", "initial")
    _run_git(
        knowledge_repo,
        "remote",
        "add",
        "origin",
        "https://github.com/Sandhiya0305/open-architecture-knowledge.git",
    )
    head = _run_git(knowledge_repo, "rev-parse", "HEAD")
    _run_git(knowledge_repo, "update-ref", "refs/remotes/origin/main", head)

    real_git = publishing._git

    def controlled_git(repo_path, *args, env=None):
        if args == ("remote", "get-url", "origin"):
            return "https://github.com/Sandhiya0305/open-architecture-knowledge.git"
        if args and args[0] in {"fetch", "ls-remote", "push"}:
            return ""
        return real_git(repo_path, *args, env=env)

    def fake_github_request(url, token, payload):
        assert token == "publish-token"
        assert payload["draft"] is True
        return {"html_url": "https://github.com/Sandhiya0305/open-architecture-knowledge/pull/99"}

    monkeypatch.setattr(publishing, "_git", controlled_git)
    monkeypatch.setattr(publishing, "_github_request", fake_github_request)
    result = publish_knowledge_candidates(
        bundle,
        knowledge_repo,
        token="publish-token",
        as_of=AS_OF,
    )

    assert result["pull_request_url"].endswith("/pull/99")
    branch = result["branch"]
    published_text = _run_git(
        knowledge_repo, "show", f"{branch}:docs/research-candidates/2026-11-13.md"
    )
    index_text = _run_git(knowledge_repo, "show", f"{branch}:docs/research-candidates/index.md")
    assert "Evidence status: UNVERIFIED" in published_text
    assert "2026-11-13.md" in index_text
    assert _run_git(knowledge_repo, "branch", "--show-current") == "main"
