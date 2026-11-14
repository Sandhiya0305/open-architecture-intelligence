"""Typed contracts for persisted OAI records."""

from typing import Any, NotRequired, TypedDict


class SourceRecord(TypedDict):
    source_id: str
    source_type: str
    url: str
    title: str
    published_at: str | None
    retrieved_at: str
    content_excerpt: NotRequired[str]
    publisher: NotRequired[str]
    publisher_type: NotRequired[str]


class ObservationRecord(TypedDict):
    schema_version: int
    observation_id: str
    source_record_id: str
    source: SourceRecord
    observed_at: str
    category: str
    architecture_matches: list[str]
    ecosystem: str
    claim: str
    claim_type: str
    evidence_status: str
    evidence_notes: str
    tags: list[str]
    metrics: dict[str, Any]
    evidence_details: NotRequired[dict[str, Any]]


class ClaimCandidate(TypedDict):
    schema_version: int
    claim_id: str
    observation_id: str
    source_url: str
    source_title: str
    publisher: NotRequired[str]
    publisher_type: NotRequired[str]
    source_id: str
    source_record_id: str
    source_type: str
    architecture_ids: list[str]
    claim_text: str
    claim_kinds: list[str]
    evidence_status: str
    review_status: str
    extraction_method: str
    review_note: str
    normalized_claim: str
    duplicate_observation_ids: list[str]
    possible_conflict_observation_ids: list[str]
    reviewer: NotRequired[str]
    reviewed_at: NotRequired[str]


class ReviewDecision(TypedDict):
    schema_version: int
    review_id: str
    claim_id: str
    decision: str
    reviewer: str
    reviewer_id: int
    source_checked: bool
    reviewed_source_url: str
    note: str
    reviewed_at: str
