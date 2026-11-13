"""Append-only human decisions and safe knowledge-candidate preparation."""

import json
import uuid
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from oai_intelligence.validation import PROJECT_ROOT, validate_review_decision

_ALLOWED_DECISIONS = {"approve", "reject", "needs-evidence"}


def _escape_markdown(value: str) -> str:
    escaped = []
    for character in value:
        if character in "\\`*_{}[]()#+.!|>":
            escaped.append("\\")
        escaped.append(character)
    return "".join(escaped)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL in {path} at line {line_number}: {exc}") from exc
            if not isinstance(value, dict):
                raise TypeError(f"Expected a JSON object in {path} at line {line_number}.")
            records.append(value)
    return records


def record_claim_review(
    claim_id: str,
    decision: str,
    reviewer: str,
    note: str,
    queue_dir: Path | None = None,
    reviews_file: Path | None = None,
    as_of: date | None = None,
) -> dict[str, Any]:
    """Append a human decision; never modify the generated claim or observation."""
    if decision not in _ALLOWED_DECISIONS:
        raise ValueError(f"Decision must be one of: {', '.join(sorted(_ALLOWED_DECISIONS))}.")
    if not claim_id.strip() or not reviewer.strip() or not note.strip():
        raise ValueError("Claim ID, reviewer, and review note are required.")
    as_of = as_of or datetime.now(UTC).date()
    queue_dir = queue_dir or PROJECT_ROOT / "reports" / "claims"
    reviews_file = reviews_file or PROJECT_ROOT / "data" / "reviews" / "claim-decisions.jsonl"
    queue_path = queue_dir / f"{as_of.isoformat()}.json"
    if not queue_path.exists():
        raise ValueError(f"Claim queue not found: {queue_path}. Run `oai claims review-queue` first.")
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    if not any(item.get("claim_id") == claim_id for item in queue):
        raise ValueError(f"Claim ID {claim_id} is not present in {queue_path}.")
    record = {
        "review_id": str(uuid.uuid4()),
        "claim_id": claim_id,
        "decision": decision,
        "reviewer": reviewer.strip(),
        "note": note.strip(),
        "reviewed_at": datetime.now(UTC).isoformat(),
    }
    validate_review_decision(record)
    reviews_file.parent.mkdir(parents=True, exist_ok=True)
    with reviews_file.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return record


def latest_review_decisions(reviews_file: Path) -> dict[str, dict[str, Any]]:
    """Return latest decision per claim while retaining the full append-only history."""
    latest: dict[str, dict[str, Any]] = {}
    for record in _read_jsonl(reviews_file):
        claim_id = record.get("claim_id")
        if not isinstance(claim_id, str) or record.get("decision") not in _ALLOWED_DECISIONS:
            raise ValueError(f"Invalid review decision record in {reviews_file}.")
        validate_review_decision(record)
        latest[claim_id] = record
    return latest


def prepare_knowledge_candidates(
    queue_dir: Path | None = None,
    reviews_file: Path | None = None,
    output_dir: Path | None = None,
    as_of: date | None = None,
) -> dict[str, Any]:
    """Create source-linked, explicitly unverified Markdown for approved candidates only."""
    as_of = as_of or datetime.now(UTC).date()
    queue_dir = queue_dir or PROJECT_ROOT / "reports" / "claims"
    reviews_file = reviews_file or PROJECT_ROOT / "data" / "reviews" / "claim-decisions.jsonl"
    output_dir = output_dir or PROJECT_ROOT / "reports" / "knowledge-candidates"
    queue_path = queue_dir / f"{as_of.isoformat()}.json"
    if not queue_path.exists():
        raise ValueError(f"Claim queue not found: {queue_path}. Run `oai claims review-queue` first.")
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    decisions = latest_review_decisions(reviews_file)
    approved = [item for item in queue if decisions.get(item.get("claim_id"), {}).get("decision") == "approve"]
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{as_of.isoformat()}.md"
    lines = [
        f"# Reviewed architecture claim candidates - {as_of.isoformat()}",
        "",
        "> **Evidence status: UNVERIFIED.** Human approval here means editorial approval to propose this candidate, not scientific verification, proof of causality, or a performance finding.",
        "",
        "Only candidates with an explicit human `approve` decision are included. Original wording is retained as a short excerpt; consult the linked source for full context. No benchmark or comparative conclusion is inferred.",
        "",
    ]
    for item in approved:
        review = decisions[item["claim_id"]]
        lines.extend([
            f"## {_escape_markdown(item['claim_text'])}",
            "",
            f"- Architecture: {', '.join(item.get('architecture_ids', [])) or 'Unclassified'}",
            f"- Claim category: {', '.join(item.get('claim_kinds', []))}",
            "- Evidence status: **UNVERIFIED**",
            f"- Source: [{_escape_markdown(item['source_title'])}](<{item['source_url']}>)",
            f"- Observation ID: `{item['observation_id']}`",
            f"- Claim ID: `{item['claim_id']}`",
            f"- Human review: {_escape_markdown(review['reviewer'])} ({review['reviewed_at']})",
            f"- Review note: {_escape_markdown(review['note'])}",
            "",
        ])
    if not approved:
        lines.append("No claims have been approved for a knowledge-update proposal in this review period.")
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "queue_claims": len(queue),
        "approved_candidates": len(approved),
        "output": str(output_path),
    }
