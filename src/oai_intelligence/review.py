"""Authenticated, append-only human decisions and knowledge-candidate preparation."""

import json
import os
import urllib.error
import urllib.request
import uuid
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, cast

from oai_intelligence.formatting import escape_markdown
from oai_intelligence.jsonl import read_jsonl_objects
from oai_intelligence.types import ClaimCandidate, ReviewDecision
from oai_intelligence.validation import PROJECT_ROOT, validate_review_decision

_ALLOWED_DECISIONS = {"approve", "reject", "needs-evidence"}
GITHUB_USER_API = "https://api.github.com/user"


class ReviewAuthenticationError(ValueError):
    """Raised when a review cannot be tied to an authenticated GitHub account."""


def _authenticated_github_user(token: str) -> dict[str, Any]:
    request = urllib.request.Request(
        GITHUB_USER_API,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "Open-Architecture-Intelligence",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read(64 * 1024 + 1))
    except urllib.error.HTTPError as exc:
        raise ReviewAuthenticationError(
            f"GitHub could not authenticate the review token (HTTP {exc.code})."
        ) from exc
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise ReviewAuthenticationError(f"Could not verify the GitHub reviewer: {exc}") from exc

    if (
        not isinstance(payload, dict)
        or not isinstance(payload.get("login"), str)
        or not isinstance(payload.get("id"), int)
    ):
        raise ReviewAuthenticationError("GitHub returned an invalid authenticated-user response.")
    return {"login": payload["login"], "id": payload["id"]}


def record_claim_review(
    claim_id: str,
    decision: str,
    reviewer: str,
    note: str,
    queue_dir: Path | None = None,
    reviews_file: Path | None = None,
    as_of: date | None = None,
    source_checked: bool = False,
    token: str | None = None,
) -> ReviewDecision:
    """Append a decision tied to the authenticated GitHub user and source-check attestation."""
    if decision not in _ALLOWED_DECISIONS:
        raise ValueError(f"Decision must be one of: {', '.join(sorted(_ALLOWED_DECISIONS))}.")
    if not claim_id.strip() or not reviewer.strip() or not note.strip():
        raise ValueError("Claim ID, reviewer, and review note are required.")
    if source_checked is not True:
        raise ValueError(
            "Confirm that you opened and checked the linked source with --source-checked."
        )

    token = token or os.environ.get("OAI_REVIEW_TOKEN")
    if not token:
        raise ReviewAuthenticationError(
            "Set OAI_REVIEW_TOKEN to a GitHub personal access token for the reviewing account."
        )
    authenticated_user = _authenticated_github_user(token)
    if reviewer.casefold() != authenticated_user["login"].casefold():
        raise ReviewAuthenticationError(
            f"Reviewer must match the authenticated GitHub account ({authenticated_user['login']})."
        )

    as_of = as_of or datetime.now(UTC).date()
    queue_dir = queue_dir or PROJECT_ROOT / "reports" / "claims"
    reviews_file = reviews_file or PROJECT_ROOT / "data" / "reviews" / "claim-decisions.jsonl"
    queue_paths = [
        path for path in sorted(queue_dir.glob("*.json")) if path.stem <= as_of.isoformat()
    ]
    if not queue_paths:
        raise ValueError(
            f"No claim queues found in {queue_dir}. Run `oai claims review-queue` first."
        )
    claims_by_id: dict[str, ClaimCandidate] = {}
    for path in queue_paths:
        items = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(items, list):
            raise TypeError(f"Claim queue must contain a JSON array: {path}")
        for item in items:
            if isinstance(item, dict) and isinstance(item.get("claim_id"), str):
                claims_by_id[item["claim_id"]] = cast(ClaimCandidate, item)
    queue = list(claims_by_id.values())
    claim = next((item for item in queue if item.get("claim_id") == claim_id), None)
    if claim is None:
        raise ValueError(f"Claim ID {claim_id} is not present in the available review queues.")
    source_url = claim.get("source_url")
    if not isinstance(source_url, str) or not source_url.startswith("https://"):
        raise ValueError("The selected claim does not contain a valid HTTPS source URL.")

    record: ReviewDecision = {
        "schema_version": 1,
        "review_id": str(uuid.uuid4()),
        "claim_id": claim_id,
        "decision": decision,
        "reviewer": authenticated_user["login"],
        "reviewer_id": authenticated_user["id"],
        "source_checked": True,
        "reviewed_source_url": source_url,
        "note": note.strip(),
        "reviewed_at": datetime.now(UTC).isoformat(),
    }
    validate_review_decision(record)
    reviews_file.parent.mkdir(parents=True, exist_ok=True)
    with reviews_file.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return record


def latest_review_decisions(reviews_file: Path) -> dict[str, ReviewDecision]:
    """Return latest decision per claim while retaining the full append-only history."""
    latest: dict[str, ReviewDecision] = {}
    for record in read_jsonl_objects(reviews_file):
        claim_id = record.get("claim_id")
        if not isinstance(claim_id, str) or record.get("decision") not in _ALLOWED_DECISIONS:
            raise ValueError(f"Invalid review decision record in {reviews_file}.")
        validate_review_decision(record)
        latest[claim_id] = cast(ReviewDecision, record)
    return latest


def prepare_knowledge_candidates(
    queue_dir: Path | None = None,
    reviews_file: Path | None = None,
    output_dir: Path | None = None,
    as_of: date | None = None,
) -> dict[str, Any]:
    """Create source-linked, explicitly unverified Markdown for authenticated approvals only."""
    as_of = as_of or datetime.now(UTC).date()
    queue_dir = queue_dir or PROJECT_ROOT / "reports" / "claims"
    reviews_file = reviews_file or PROJECT_ROOT / "data" / "reviews" / "claim-decisions.jsonl"
    output_dir = output_dir or PROJECT_ROOT / "reports" / "knowledge-candidates"
    queue_paths = [
        path for path in sorted(queue_dir.glob("*.json")) if path.stem <= as_of.isoformat()
    ]
    if not queue_paths:
        raise ValueError(
            f"No claim queues found in {queue_dir}. Run `oai claims review-queue` first."
        )
    claims_by_id: dict[str, ClaimCandidate] = {}
    for path in queue_paths:
        items = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(items, list):
            raise TypeError(f"Claim queue must contain a JSON array: {path}")
        for item in items:
            if isinstance(item, dict) and isinstance(item.get("claim_id"), str):
                claims_by_id[item["claim_id"]] = cast(ClaimCandidate, item)
    queue = list(claims_by_id.values())
    decisions = latest_review_decisions(reviews_file)
    approved = [
        item
        for item in queue
        if (decision := decisions.get(item["claim_id"])) is not None
        and decision["decision"] == "approve"
    ]
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{as_of.isoformat()}.md"
    lines = [
        f"# Reviewed architecture claim candidates - {as_of.isoformat()}",
        "",
        (
            "> **Evidence status: UNVERIFIED.** Human approval here means editorial "
            "approval to propose this candidate, not scientific verification, proof "
            "of causality, or a performance finding."
        ),
        "",
        (
            "Only candidates with an explicit authenticated GitHub review decision are included. "
            "The reviewer attests that the linked source was opened and checked. Original "
            "wording is retained as a short excerpt; consult the linked source for full context. "
            "No benchmark or comparative conclusion is inferred."
        ),
        "",
    ]
    for item in approved:
        review = decisions[item["claim_id"]]
        lines.extend(
            [
                f"## {escape_markdown(item['claim_text'])}",
                "",
                f"- Architecture: {', '.join(item.get('architecture_ids', [])) or 'Unclassified'}",
                f"- Claim category: {', '.join(item.get('claim_kinds', []))}",
                "- Evidence status: **UNVERIFIED**",
                f"- Source: [{escape_markdown(item['source_title'])}](<{item['source_url']}>)",
                f"- Observation ID: `{item['observation_id']}`",
                f"- Claim ID: `{item['claim_id']}`",
                f"- Human review: {escape_markdown(review['reviewer'])} "
                f"(GitHub user ID {review['reviewer_id']}, {review['reviewed_at']})",
                f"- Source checked: {review['reviewed_source_url']}",
                f"- Review note: {escape_markdown(review['note'])}",
                "",
            ]
        )
    if not approved:
        lines.append(
            "No claims have been approved for a knowledge-update proposal in this review period."
        )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "queue_claims": len(queue),
        "approved_candidates": len(approved),
        "output": str(output_path),
    }
