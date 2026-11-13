"""Prepare and open a review-only PR in the separate knowledge repository."""

import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

EXPECTED_REMOTE = "github.com/Sandhiya0305/open-architecture-knowledge"


class PublishingError(RuntimeError):
    """Raised when a safe knowledge pull request cannot be prepared."""


def _git(repo_path: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo_path, check=False, capture_output=True, text=True
    )
    if result.returncode:
        raise PublishingError(result.stderr.strip() or result.stdout.strip() or "Git command failed.")
    return result.stdout.strip()


def _github_request(url: str, token: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "Open-Architecture-Intelligence",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        raise PublishingError(f"GitHub rejected pull request creation ({exc.code}): {detail}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise PublishingError(f"Could not reach GitHub to create pull request: {exc}") from exc


def publish_knowledge_candidates(
    bundle_path: Path,
    repo_path: Path,
    token: str | None = None,
    base_branch: str = "main",
    as_of: date | None = None,
) -> dict[str, str]:
    """Commit an approved, unverified candidate bundle to a new branch and open a PR."""
    token = token or os.environ.get("OAI_GITHUB_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise PublishingError(
            "Set OAI_GITHUB_TOKEN to a fine-grained token with Contents: Read and write "
            "and Pull requests: Read and write on Sandhiya0305/open-architecture-knowledge."
        )
    if not bundle_path.is_file():
        raise PublishingError(f"Knowledge candidate bundle not found: {bundle_path}")
    content = bundle_path.read_text(encoding="utf-8")
    required_markers = (
        "Evidence status: UNVERIFIED", "Human approval", "- Claim ID:",
        "- Human review:", "- Source: [",
    )
    if any(marker not in content for marker in required_markers):
        raise PublishingError(
            "Bundle is empty or missing mandatory source, claim-ID, human-review, or unverified safeguards."
        )
    if not repo_path.is_dir() or not (repo_path / ".git").exists():
        raise PublishingError(f"Not a Git repository: {repo_path}")
    if _git(repo_path, "status", "--porcelain"):
        raise PublishingError("Knowledge repository has uncommitted changes. Commit or stash them first.")
    remote = _git(repo_path, "remote", "get-url", "origin").lower().removesuffix(".git")
    allowed_remotes = {
        "https://" + EXPECTED_REMOTE.lower(),
        "http://" + EXPECTED_REMOTE.lower(),
        "git@" + EXPECTED_REMOTE.lower().replace("/", ":", 1),
    }
    if remote not in allowed_remotes:
        raise PublishingError(f"Refusing to publish: unexpected origin remote {remote!r}.")
    if not re.fullmatch(r"[A-Za-z0-9._/-]+", base_branch) or base_branch.startswith("-"):
        raise PublishingError("Invalid base branch name.")

    as_of = as_of or datetime.now(UTC).date()
    branch = f"oai/knowledge-candidates-{as_of:%Y%m%d}"
    target = repo_path / "evidence" / "candidates" / f"{as_of.isoformat()}.md"
    if target.exists():
        raise PublishingError(f"Refusing to overwrite existing knowledge candidate file: {target}")
    _git(repo_path, "fetch", "origin", base_branch)
    existing = _git(repo_path, "ls-remote", "--heads", "origin", f"refs/heads/{branch}")
    if existing or _git(repo_path, "branch", "--list", branch):
        raise PublishingError(f"Branch {branch} already exists; inspect it before retrying.")
    _git(repo_path, "switch", "--create", branch, f"origin/{base_branch}")
    if target.exists():
        raise PublishingError(f"Refusing to overwrite existing knowledge candidate file: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    _git(repo_path, "add", str(target.relative_to(repo_path)))
    _git(repo_path, "commit", "-m", f"docs: propose reviewed architecture candidates {as_of.isoformat()}")
    _git(repo_path, "push", "--set-upstream", "origin", branch)

    payload = {
        "title": f"OAI: reviewed architecture claim candidates ({as_of.isoformat()})",
        "head": branch,
        "base": base_branch,
        "body": (
            "## Purpose\n\n"
            "Proposes source-linked architecture claim candidates that received an explicit human "
            "editorial approval in Open Architecture Intelligence.\n\n"
            "## Evidence safeguards\n\n"
            "- Every candidate remains **UNVERIFIED**. Editorial approval is not scientific verification.\n"
            "- Original source links and observation IDs are retained.\n"
            "- No performance comparison or causal conclusion is inferred.\n"
            "- This pull request requires human review and must not be auto-merged.\n"
        ),
        "draft": True,
    }
    try:
        pr = _github_request(
            "https://api.github.com/repos/Sandhiya0305/open-architecture-knowledge/pulls",
            token,
            payload,
        )
    except PublishingError as exc:
        raise PublishingError(
            f"The branch {branch} was pushed, but the pull request could not be created. "
            f"Inspect the branch before retrying. Details: {exc}"
        ) from exc
    return {"branch": branch, "pull_request_url": pr.get("html_url", ""), "title": payload["title"]}
