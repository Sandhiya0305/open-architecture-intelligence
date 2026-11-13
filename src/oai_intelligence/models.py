"""Canonical observation construction and validation."""

import hashlib
import re
from datetime import UTC, datetime
from typing import Any

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


def classify_architectures(
    repository: dict[str, Any], taxonomy: dict[str, Any]
) -> list[str]:
    searchable = " ".join(
        [
            str(repository.get("name", "")),
            str(repository.get("full_name", "")),
            str(repository.get("description") or ""),
            " ".join(repository.get("topics") or []),
        ]
    )
    matches: list[str] = []
    for architecture in taxonomy.get("architectures", []):
        terms = [architecture["name"], architecture["id"], *architecture.get("aliases", [])]
        if any(_matches(searchable, term) for term in terms):
            matches.append(architecture["id"])
    return matches


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def repository_observation(
    repository: dict[str, Any],
    ecosystem: str,
    taxonomy: dict[str, Any],
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    observed_at = observed_at or utc_now()
    timestamp = _timestamp(observed_at)
    full_name = repository["full_name"]
    source_url = repository["html_url"]
    matches = classify_architectures(repository, taxonomy)
    category = matches[0] if matches else "unclassified"
    identity = f"github:{full_name.casefold()}:{observed_at.date().isoformat()}"
    observation_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    license_info = repository.get("license") or {}

    observation = {
        "observation_id": observation_id,
        "source_record_id": f"github:{full_name}",
        "source": {
            "source_id": "github",
            "source_type": "repository",
            "url": source_url,
            "title": full_name,
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
    validate_observation(observation)
    return observation


def discussion_observation(
    story: dict[str, Any],
    taxonomy: dict[str, Any],
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    observed_at = observed_at or utc_now()
    timestamp = _timestamp(observed_at)
    object_id = str(story.get("objectID") or "")
    title = str(story.get("title") or "").strip()
    if not object_id or not title:
        raise ValueError("Hacker News stories must include objectID and title.")

    searchable = " ".join(
        [title, str(story.get("story_text") or ""), str(story.get("url") or "")]
    )
    matches = classify_architectures(
        {"name": title, "description": searchable, "topics": []}, taxonomy
    )
    published_at = story.get("created_at")
    source_url = f"https://news.ycombinator.com/item?id={object_id}"
    identity = f"hacker_news:{object_id}:{observed_at.date().isoformat()}"
    observation_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()

    observation = {
        "observation_id": observation_id,
        "source_record_id": f"hacker_news:{object_id}",
        "source": {
            "source_id": "hacker_news",
            "source_type": "discussion",
            "url": source_url,
            "title": title,
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
    validate_observation(observation)
    return observation
