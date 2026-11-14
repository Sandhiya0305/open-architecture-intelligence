"""Canonical observation construction and validation."""

import hashlib
import json
import re
from datetime import UTC, datetime
from typing import Any

from oai_intelligence.types import ObservationRecord
from oai_intelligence.validation import validate_observation


def utc_now() -> datetime:
    return datetime.now(UTC)


def _matches(text: str, term: str) -> bool:
    normalized = term.casefold().strip()
    if len(normalized) < 4:
        return False
    haystack = re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()
    needle = re.sub(r"[^a-z0-9]+", " ", normalized).strip()
    return f" {needle} " in f" {haystack} "


_ARCHITECTURE_CONTEXT = (
    "software",
    "system",
    "application",
    "backend",
    "domain",
    "deployment",
    "module boundaries",
    "message broker",
    "reference implementation",
    "design pattern",
    "presentation",
    "persistence",
    "implementation",
    "codebase",
    "service discovery",
    "domain events",
    "example",
    "demo",
    "sample",
    "guide",
    "tutorial",
    "dependency direction",
)


def classify_architectures(repository: dict[str, Any], taxonomy: dict[str, Any]) -> list[str]:
    """Classify only when a pattern term has descriptive or explicit topic context."""
    name = " ".join([str(repository.get("name", "")), str(repository.get("full_name", ""))])
    description = str(repository.get("description") or "")
    topics = " ".join(repository.get("topics") or [])
    descriptive_text = " ".join([description, topics, name])
    has_context = any(_matches(descriptive_text, term) for term in _ARCHITECTURE_CONTEXT)

    matches: list[str] = []
    for architecture in taxonomy.get("architectures", []):
        terms = [architecture["name"], *architecture.get("aliases", [])]
        explicit_topic_match = any(_matches(topics, term) for term in terms)
        description_match = has_context and any(_matches(description, term) for term in terms)
        name_match = has_context and any(_matches(name, term) for term in terms)
        if explicit_topic_match or description_match or name_match:
            matches.append(architecture["id"])
    return matches


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _snapshot_observation_id(observation: ObservationRecord) -> str:
    """Fingerprint source content and measured metadata, excluding retrieval times."""
    snapshot = {
        key: value
        for key, value in observation.items()
        if key not in {"observation_id", "observed_at"}
    }
    source = dict(observation["source"])
    source.pop("retrieved_at", None)
    snapshot["source"] = source
    serialized = json.dumps(
        snapshot,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def repository_observation(
    repository: dict[str, Any],
    ecosystem: str,
    taxonomy: dict[str, Any],
    observed_at: datetime | None = None,
) -> ObservationRecord:
    observed_at = observed_at or utc_now()
    timestamp = _timestamp(observed_at)
    full_name = repository["full_name"]
    source_url = repository["html_url"]
    matches = classify_architectures(repository, taxonomy)
    category = matches[0] if matches else "unclassified"
    license_info = repository.get("license") or {}

    observation: ObservationRecord = {
        "schema_version": 1,
        "observation_id": "",
        "source_record_id": f"github:{full_name}",
        "source": {
            "source_id": "github",
            "source_type": "repository",
            "url": source_url,
            "title": full_name,
            "content_excerpt": str(repository.get("description") or "")[:4000],
            "published_at": None,
            "retrieved_at": timestamp,
        },
        "observed_at": timestamp,
        "category": category,
        "architecture_matches": matches,
        "ecosystem": ecosystem,
        "claim": (
            "Repository metadata matched configured architecture discovery terms. "
            "This is a candidate for review, not proof of adoption, implementation quality, "
            "or performance."
        ),
        "claim_type": "discovery_candidate",
        "evidence_status": "unverified",
        "evidence_notes": (
            "Classification uses repository name, description, and topics only. "
            "Review source content before making architecture claims."
        ),
        "tags": [ecosystem, *matches],
        "metrics": {
            "stars": repository.get("stargazers_count", 0),
            "forks": repository.get("forks_count", 0),
            "open_issues": repository.get("open_issues_count", 0),
            "primary_language": repository.get("language"),
            "created_at": repository.get("created_at"),
            "updated_at": repository.get("updated_at"),
            "pushed_at": repository.get("pushed_at"),
            "default_branch": repository.get("default_branch"),
            "archived": repository.get("archived", False),
            "license_spdx_id": license_info.get("spdx_id"),
        },
    }
    observation["observation_id"] = _snapshot_observation_id(observation)
    validate_observation(observation)
    return observation


def discussion_observation(
    story: dict[str, Any],
    taxonomy: dict[str, Any],
    observed_at: datetime | None = None,
) -> ObservationRecord:
    observed_at = observed_at or utc_now()
    timestamp = _timestamp(observed_at)
    object_id = str(story.get("objectID") or "")
    title = str(story.get("title") or "").strip()
    if not object_id or not title:
        raise ValueError("Hacker News stories must include objectID and title.")

    searchable = " ".join([title, str(story.get("story_text") or ""), str(story.get("url") or "")])
    matches = classify_architectures(
        {"name": title, "description": searchable, "topics": []}, taxonomy
    )
    published_at = story.get("created_at")
    source_url = f"https://news.ycombinator.com/item?id={object_id}"

    observation: ObservationRecord = {
        "schema_version": 1,
        "observation_id": "",
        "source_record_id": f"hacker_news:{object_id}",
        "source": {
            "source_id": "hacker_news",
            "source_type": "discussion",
            "url": source_url,
            "title": title,
            "content_excerpt": str(story.get("story_text") or "")[:4000],
            "published_at": published_at,
            "retrieved_at": timestamp,
        },
        "observed_at": timestamp,
        "category": matches[0] if matches else "unclassified",
        "architecture_matches": matches,
        "ecosystem": "cross_ecosystem",
        "claim": (
            "A Hacker News story matched configured architecture discovery terms. "
            "Discussion activity is an interest signal, not proof of adoption, quality, "
            "or performance."
        ),
        "claim_type": "discussion",
        "evidence_status": "unverified",
        "evidence_notes": (
            "This record captures a public discussion and its metadata only. "
            "Review the linked story and its context before drawing conclusions."
        ),
        "tags": ["hacker-news", "discussion", *matches],
        "metrics": {
            "points": story.get("points"),
            "comment_count": story.get("num_comments"),
            "author": story.get("author"),
            "story_url": story.get("url"),
        },
    }
    observation["observation_id"] = _snapshot_observation_id(observation)
    validate_observation(observation)
    return observation


def article_observation(
    article: dict[str, Any],
    taxonomy: dict[str, Any],
    observed_at: datetime | None = None,
) -> ObservationRecord:
    observed_at = observed_at or utc_now()
    timestamp = _timestamp(observed_at)
    article_url = str(article.get("url") or "")
    title = str(article.get("title") or "").strip()
    feed_id = str(article.get("feed_id") or "")
    entry_id = str(article.get("entry_id") or article_url)
    if not article_url.startswith("https://") or not title or not feed_id:
        raise ValueError("RSS articles require a title, feed_id, and HTTPS article URL.")

    summary = str(article.get("summary") or "")
    searchable = " ".join([title, summary])
    matches = classify_architectures(
        {"name": title, "description": searchable, "topics": []}, taxonomy
    )
    publisher = str(article.get("publisher") or article.get("feed_title") or feed_id)

    observation: ObservationRecord = {
        "schema_version": 1,
        "observation_id": "",
        "source_record_id": f"rss:{feed_id}:{entry_id}",
        "source": {
            "source_id": "rss",
            "source_type": "article",
            "url": article_url,
            "title": title,
            "publisher": publisher,
            "publisher_type": str(article.get("publisher_type") or "unspecified"),
            "content_excerpt": str(article.get("summary") or "")[:4000],
            "published_at": article.get("published_at"),
            "retrieved_at": timestamp,
        },
        "observed_at": timestamp,
        "category": matches[0] if matches else "unclassified",
        "architecture_matches": matches,
        "ecosystem": "cross_ecosystem",
        "claim": (
            f"An article from {publisher} matched configured architecture discovery terms. "
            "This is a research candidate, not independently verified evidence."
        ),
        "claim_type": "discovery_candidate",
        "evidence_status": "unverified",
        "evidence_notes": (
            "Classification uses article title and feed summary only. Performance "
            "assessment is applied to extracted statements, not unrelated wording in "
            "the wider summary. The full article has not been reviewed or corroborated."
        ),
        "tags": ["rss", "article", publisher, *matches],
        "metrics": {},
    }
    details = article.get("evidence_details")
    if isinstance(details, dict):
        observation["evidence_details"] = details
    observation["observation_id"] = _snapshot_observation_id(observation)
    validate_observation(observation)
    return observation
