"""Conservative, deterministic claim candidates and human review queues."""

import hashlib
import json
import re
from collections import defaultdict
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from oai_intelligence.validation import PROJECT_ROOT

# Only sentences containing explicit trade-off / outcome language become candidates.
_CLAIM_PATTERNS = {
    "benefit": re.compile(r"\b(improv(?:e|es|ed|ement)|reduc(?:e|es|ed|tion)|increas(?:e|es|ed)|faster|lower|higher|scalab(?:le|ility)|resilien(?:t|ce))\b", re.IGNORECASE),
    "limitation": re.compile(r"\b(limit(?:ation|ations|ed)?|drawback|trade[- ]off|overhead|complexity|challeng(?:e|es|ing)|bottleneck|difficult)\b", re.IGNORECASE),
    "decision": re.compile(r"\b(chose|chosen|adopt(?:ed|s)?|migrat(?:e|ed|ion)|decid(?:e|ed)|prefer(?:red|s)?)\b", re.IGNORECASE),
}


def _sentences(text: str) -> list[str]:
    return [part.strip(" \t\r\n-•") for part in re.split(r"(?<=[.!?])\s+|\n+", text) if part.strip()]


def _normalize(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.casefold()))


def extract_claim_candidates(observation: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract candidate sentences only from captured source text, never metadata metrics."""
    source = observation.get("source", {})
    excerpt = str(source.get("content_excerpt") or "")
    if not excerpt.strip():
        return []

    candidates = []
    for sentence in _sentences(excerpt):
        if len(sentence) < 35 or len(sentence) > 600:
            continue
        matched = [kind for kind, pattern in _CLAIM_PATTERNS.items() if pattern.search(sentence)]
        if not matched:
            continue
        normalized = _normalize(sentence)
        if len(normalized.split()) < 6:
            continue
        fingerprint = hashlib.sha256(
            f"{','.join(sorted(observation.get('architecture_matches', [])))}:{normalized}".encode()
        ).hexdigest()
        candidates.append({
            "claim_id": fingerprint,
            "observation_id": observation["observation_id"],
            "source_url": source["url"],
            "source_title": source["title"],
            "source_id": source["source_id"],
            "architecture_ids": sorted(observation.get("architecture_matches", [])),
            "claim_text": sentence,
            "claim_kinds": matched,
            "evidence_status": "unverified",
            "review_status": "pending",
            "extraction_method": "deterministic_sentence_rules",
            "review_note": "Candidate extracted from captured source text; verify the full source and context.",
            "normalized_claim": normalized,
        })
    return candidates


def build_review_queue(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = [claim for item in observations for claim in extract_claim_candidates(item)]
    groups: dict[tuple[tuple[str, ...], str], list[dict[str, Any]]] = defaultdict(list)
    for claim in candidates:
        groups[(tuple(claim["architecture_ids"]), claim["normalized_claim"])].append(claim)

    queue = []
    for claim in candidates:
        peers = groups[(tuple(claim["architecture_ids"]), claim["normalized_claim"])]
        claim = dict(claim)
        claim["duplicate_observation_ids"] = sorted({
            peer["observation_id"] for peer in peers if peer["observation_id"] != claim["observation_id"]
        })
        # Opposing polarity is only a review flag, not a conclusion that sources conflict.
        text = claim["claim_text"].casefold()
        opposing = []
        for other in candidates:
            if other["observation_id"] == claim["observation_id"]:
                continue
            if other["architecture_ids"] != claim["architecture_ids"]:
                continue
            other_text = other["claim_text"].casefold()
            same_subject = set(_normalize(text).split()) & set(_normalize(other_text).split())
            if len(same_subject) >= 5 and (("increase" in text and "decrease" in other_text) or ("decrease" in text and "increase" in other_text) or ("improve" in text and "worsen" in other_text) or ("worsen" in text and "improve" in other_text)):
                opposing.append(other["observation_id"])
        claim["possible_conflict_observation_ids"] = sorted(set(opposing))
        if claim["duplicate_observation_ids"]:
            claim["review_note"] += " Similar exact claim found in another observation; inspect source independence."
        if claim["possible_conflict_observation_ids"]:
            claim["review_note"] += " Potentially opposing wording found; compare workloads and context."
        queue.append(claim)
    return queue


def generate_claim_review_queue(
    data_dir: Path | None = None,
    output_dir: Path | None = None,
    as_of: date | None = None,
) -> dict[str, Any]:
    data_dir = data_dir or PROJECT_ROOT / "data" / "observations"
    output_dir = output_dir or PROJECT_ROOT / "reports" / "claims"
    as_of = as_of or datetime.now(UTC).date()
    observations = []
    for path in sorted(data_dir.glob("*.jsonl")):
        if path.stem > as_of.isoformat():
            continue
        with path.open(encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, start=1):
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSONL in {path} at line {line_number}: {exc}") from exc
                if not isinstance(item, dict) or "observation_id" not in item:
                    raise ValueError(f"Invalid observation in {path} at line {line_number}.")
                observations.append(item)

    queue = build_review_queue(observations)
    output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = output_dir / f"{as_of.isoformat()}.jsonl"
    json_path = output_dir / f"{as_of.isoformat()}.json"
    markdown_path = output_dir / f"{as_of.isoformat()}.md"
    with jsonl_path.open("w", encoding="utf-8", newline="\n") as stream:
        for item in queue:
            stream.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")
    json_path.write_text(json.dumps(queue, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [f"# Claim review queue — {as_of.isoformat()}", "",
             f"Candidate claims: **{len(queue)}**", "",
             "All items are unverified candidates. Extraction does not establish truth, causality, or independent corroboration.", ""]
    for index, item in enumerate(queue, start=1):
        lines.extend([f"## {index}. {item['claim_text']}", "",
                      f"- Type: {', '.join(item['claim_kinds'])}",
                      f"- Architecture: {', '.join(item['architecture_ids']) or 'Unclassified'}",
                      f"- Source: [{item['source_title']}]({item['source_url']})",
                      f"- Observation: `{item['observation_id']}`",
                      f"- Review: {item['review_status']} / {item['evidence_status']}",
                      f"- Note: {item['review_note']}", ""])
    markdown_path.write_text("\n".join(lines), encoding="utf-8")
    return {"observations_scanned": len(observations), "claims_extracted": len(queue),
            "claims_with_duplicates": sum(bool(x["duplicate_observation_ids"]) for x in queue),
            "claims_with_possible_conflicts": sum(bool(x["possible_conflict_observation_ids"]) for x in queue),
            "jsonl": str(jsonl_path), "json": str(json_path), "markdown": str(markdown_path)}
