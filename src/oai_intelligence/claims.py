"""Conservative extraction of architecture-specific statements from publisher articles."""

import hashlib
import html
import json
import re
from collections import defaultdict
from datetime import UTC, date, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from oai_intelligence.formatting import escape_markdown
from oai_intelligence.reports import load_observations
from oai_intelligence.review import latest_review_decisions
from oai_intelligence.types import ClaimCandidate, ObservationRecord
from oai_intelligence.validation import PROJECT_ROOT, validate_claim

_CLAIM_PATTERNS = {
    "benefit": re.compile(
        r"\b(improv(?:e|es|ed|ement)|reduc(?:e|es|ed|tion)|increas(?:e|es|ed)|"
        r"faster|lower|higher|scalab(?:le|ility)|resilien(?:t|ce))\b",
        re.IGNORECASE,
    ),
    "limitation": re.compile(
        r"\b(limit(?:ation|ations|ed)?|drawback|trade[- ]off|overhead|complexity|"
        r"challeng(?:e|es|ing)|bottleneck|difficult)\b",
        re.IGNORECASE,
    ),
    "decision": re.compile(
        r"\b(chose|chosen|adopt(?:ed|s)?|migrat(?:e|ed|ion)|decid(?:e|ed)|"
        r"prefer(?:red|s)?)\b",
        re.IGNORECASE,
    ),
}
_CONTEXT_TERMS = re.compile(
    r"\b(by|because|due to|through|compared with|compared to|versus|"
    r"as a result|in response to|to support|to avoid|after adopting|"
    r"which (?:reduced|increased|improved|introduced|required))\b",
    re.IGNORECASE,
)
_ARCHITECTURE_TERMS = re.compile(
    r"\b(architecture|architectural|microservices?|monolith(?:ic)?|"
    r"event[- ]driven|layered|hexagonal|clean architecture|modular|"
    r"service[- ]oriented|serverless|micro[- ]frontends?|cqrs|event sourcing|"
    r"api gateway|backend[- ]for[- ]frontend|bff)\b",
    re.IGNORECASE,
)


class _HTMLText(HTMLParser):
    """Convert markup to readable text without retaining tags."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def text(self) -> str:
        return " ".join(" ".join(self.parts).split())


def _clean_text(value: str) -> str:
    parser = _HTMLText()
    parser.feed(html.unescape(value))
    parser.close()
    return parser.text()


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [part.strip(" \t\r\n-") for part in parts if part.strip()]


def _normalize(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.casefold()))


def extract_claim_candidates(observation: ObservationRecord) -> list[ClaimCandidate]:
    """Extract review leads only from curated article text, never metadata or discussion."""
    source = observation.get("source", {})
    if source.get("source_type") != "article":
        return []
    publisher_type = source.get("publisher_type")
    if publisher_type not in {"editorial", "practitioner", "research"}:
        return []

    excerpt = _clean_text(str(source.get("content_excerpt") or ""))
    source_url = str(source.get("url") or "")
    parsed_url = urlsplit(source_url)
    if parsed_url.scheme != "https" or not parsed_url.hostname or not excerpt:
        return []

    source_record_id = str(observation.get("source_record_id") or "")
    if not source_record_id:
        return []

    candidates: list[ClaimCandidate] = []
    for sentence in _sentences(excerpt):
        # Reject fragments and feed-summary truncation rather than publishing broken text.
        if len(sentence) < 45 or len(sentence) > 600:
            continue
        if not sentence.endswith((".", "!", "?")) or sentence.endswith("..."):
            continue
        if not _ARCHITECTURE_TERMS.search(sentence):
            continue
        matched = [kind for kind, pattern in _CLAIM_PATTERNS.items() if pattern.search(sentence)]
        if not matched or not _CONTEXT_TERMS.search(sentence):
            continue
        normalized = _normalize(sentence)
        if len(normalized.split()) < 7:
            continue

        fingerprint = hashlib.sha256(
            f"{source_record_id}:{source_url}:{normalized}".encode()
        ).hexdigest()
        candidate: ClaimCandidate = {
            "schema_version": 1,
            "claim_id": fingerprint,
            "observation_id": observation["observation_id"],
            "source_url": source_url,
            "source_title": str(source.get("title") or source_url),
            "publisher": str(source.get("publisher") or source.get("title") or source_url),
            "publisher_type": publisher_type,
            "source_id": str(source["source_id"]),
            "source_record_id": source_record_id,
            "source_type": "article",
            "architecture_ids": sorted(observation.get("architecture_matches", [])),
            "claim_text": sentence,
            "claim_kinds": matched,
            "evidence_status": "unverified",
            "review_status": "pending",
            "extraction_method": "architecture_sentence_rules_v3",
            "review_note": (
                "Candidate extracted from a curated-feed article summary. "
                "Publisher perspective is recorded but is not a credibility score. "
                "The full source, author context, and supporting evidence "
                "have not been independently assessed."
            ),
            "normalized_claim": normalized,
            "duplicate_observation_ids": [],
            "possible_conflict_observation_ids": [],
        }
        validate_claim(candidate)
        candidates.append(candidate)
    return candidates


def build_review_queue(observations: list[ObservationRecord]) -> list[ClaimCandidate]:
    # Stable claim IDs and source_record_id collapse repeated daily observations of one source.
    unique: dict[str, ClaimCandidate] = {}
    for observation in observations:
        for claim in extract_claim_candidates(observation):
            unique.setdefault(claim["claim_id"], claim)

    candidates = list(unique.values())
    groups: dict[tuple[tuple[str, ...], str], list[ClaimCandidate]] = defaultdict(list)
    for claim in candidates:
        groups[(tuple(claim["architecture_ids"]), claim["normalized_claim"])].append(claim)

    queue: list[ClaimCandidate] = []
    for claim in candidates:
        item = claim.copy()
        peers = groups[(tuple(item["architecture_ids"]), item["normalized_claim"])]
        independent_peers = [
            peer for peer in peers if peer["source_record_id"] != item["source_record_id"]
        ]
        item["duplicate_observation_ids"] = sorted(
            {peer["observation_id"] for peer in independent_peers}
        )
        if independent_peers:
            item["review_note"] += (
                " Similar wording appears in another source; independence and source "
                "relationship require human inspection."
            )
        validate_claim(item)
        queue.append(item)
    return queue


def generate_claim_review_queue(
    data_dir: Path | None = None,
    output_dir: Path | None = None,
    as_of: date | None = None,
    reviews_file: Path | None = None,
) -> dict[str, Any]:
    data_dir = data_dir or PROJECT_ROOT / "data" / "observations"
    output_dir = output_dir or PROJECT_ROOT / "reports" / "claims"
    reviews_file = reviews_file or PROJECT_ROOT / "data" / "reviews" / "claim-decisions.jsonl"
    as_of = as_of or datetime.now(UTC).date()
    observations = load_observations(data_dir, as_of=as_of)
    observation_dates = {
        str(item["observation_id"]): str(item["observed_at"])[:10] for item in observations
    }
    queue = [
        claim
        for claim in build_review_queue(observations)
        if observation_dates.get(claim["observation_id"]) == as_of.isoformat()
    ]
    decisions = latest_review_decisions(reviews_file)
    for claim in queue:
        decision = decisions.get(claim["claim_id"])
        if decision:
            claim["review_status"] = decision["decision"]
            claim["reviewer"] = decision["reviewer"]
            claim["reviewed_at"] = decision["reviewed_at"]
            claim["review_note"] += f" Latest human review: {decision['note']}"
        validate_claim(claim)

    output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = output_dir / f"{as_of.isoformat()}.jsonl"
    json_path = output_dir / f"{as_of.isoformat()}.json"
    markdown_path = output_dir / f"{as_of.isoformat()}.md"
    with jsonl_path.open("w", encoding="utf-8", newline="\n") as stream:
        for item in queue:
            stream.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")
    json_path.write_text(json.dumps(queue, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        f"# Claim review queue - {as_of.isoformat()}",
        "",
        f"Candidate claims: **{len(queue)}**",
        "",
        (
            "All items are unverified review leads. Extraction does not establish truth, causality, "
            + "independent corroboration, or source credibility."
        ),
        "",
    ]
    for index, item in enumerate(queue, start=1):
        lines.extend(
            [
                f"## {index}. {escape_markdown(item['claim_text'])}",
                "",
                f"- Type: {', '.join(item['claim_kinds'])}",
                f"- Publisher: {escape_markdown(item.get('publisher', 'Unspecified publisher'))} ({item.get('publisher_type', 'unspecified')})",
                f"- Architecture: {', '.join(item['architecture_ids']) or 'Unclassified'}",
                f"- Source: [{escape_markdown(item['source_title'])}](<{item['source_url']}>)",
                f"- Observation: `{item['observation_id']}`",
                f"- Claim ID: `{item['claim_id']}`",
                f"- Review: {item['review_status']} / {item['evidence_status']}",
                f"- Reviewer: {item.get('reviewer', 'Not yet reviewed')}",
                f"- Note: {escape_markdown(item['review_note'])}",
                "",
            ]
        )
    markdown_path.write_text("\n".join(lines), encoding="utf-8")
    return {
        "observations_scanned": len(observations),
        "claims_extracted": len(queue),
        "claims_with_duplicates": sum(bool(x["duplicate_observation_ids"]) for x in queue),
        "claims_with_possible_conflicts": 0,
        "jsonl": str(jsonl_path),
        "json": str(json_path),
        "markdown": str(markdown_path),
    }
